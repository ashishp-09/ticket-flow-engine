from typing import Any, Optional, Sequence, Type, Union

from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..expressions import F
from ..filters.applier import QueryFilterApplier
from ..operators import OPERATORS


class MutationQueryExecutor:
    @staticmethod
    def _process_returning(
            stmt: Any,
            current_model: Any,
            returning: Union[bool, Sequence[Any]]
    ) -> tuple[Any, bool]:
        if returning is False:
            return stmt, False

        if isinstance(returning, (list, tuple, set)):
            return stmt.returning(*returning), True

        return stmt.returning(current_model), True

    @staticmethod
    async def create(
            query: Any,
            m_data: Optional[list[dict[str, Any]]] = None,
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Union[bool, Sequence[Any]] = True,
            **kwargs: Any
    ) -> Any:
        current_model = query._get_current_model()
        raw_items = m_data if m_data is not None else [kwargs]

        if not raw_items:
            return [] if m_data is not None else None

        if query._filters:
            for item in raw_items:
                for filter_key, filter_val in query._filters.items():
                    if "__" not in filter_key and filter_key not in item:
                        item[filter_key] = filter_val

        if query._context_history:
            target_prop = query._prop_meta
            local_col = target_prop.local_columns.copy().pop()
            remote_col = target_prop.remote_side.copy().pop()

            parent_filters = query._context_history[-1]._where_criteria
            parent_id_val = None
            for criterion in parent_filters:
                if hasattr(criterion, "left") and hasattr(criterion, "right"):
                    if criterion.left.name == local_col.name:
                        parent_id_val = criterion.right.value
                        break

            if parent_id_val is not None:
                fk_field_name = remote_col.name if remote_col.table == current_model.__table__ else local_col.name
                for item in raw_items:
                    if fk_field_name not in item:
                        item[fk_field_name] = parent_id_val

        chunk_size = 1000
        all_dtos = []
        total_inserted = 0

        for i in range(0, len(raw_items), chunk_size):
            chunk = raw_items[i:i + chunk_size]
            stmt = pg_insert(current_model).values(chunk)

            if on_conflict_do_nothing:
                if index_elements:
                    stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
                else:
                    stmt = stmt.on_conflict_do_nothing()

            stmt, has_returning = MutationQueryExecutor._process_returning(stmt, current_model, returning)
            mod_res = await query._repo._execute_modification(stmt)

            if has_returning:
                chunk_dtos = query._repo._to_dto(mod_res.returning_rows)
                all_dtos.extend(chunk_dtos)
            else:
                total_inserted += mod_res.rowcount

        if returning is False:
            return total_inserted

        if m_data is not None:
            return all_dtos

        return all_dtos[0] if all_dtos else None

    @staticmethod
    async def update(
            query: Any,
            returning: Union[bool, Sequence[Any]] = True,
            **kwargs: Any
    ) -> Any:
        current_model = query._get_current_model()
        q, _ = await query._execute()
        update_values = {}

        for k, v in kwargs.items():
            if isinstance(v, F):
                update_values[k] = v.resolve(current_model)
            else:
                update_values[k] = v

        update_q = update(current_model).values(**update_values)
        if q._where_criteria:
            update_q = update_q.where(*q._where_criteria)

        update_q, has_returning = MutationQueryExecutor._process_returning(update_q, current_model, returning)
        res = await query._repo._execute_modification(update_q)
        await query._repo._session.flush()

        if not has_returning:
            return res.rowcount

        if not res.returning_rows:
            return None

        dto_list = query._to_dto(res.returning_rows)

        if isinstance(returning, (list, tuple, set)):
            return dto_list

        return dto_list[0] if dto_list else None

    @staticmethod
    def _apply_filters(query: Any, current_model: Type[Any], stmt: Any) -> Any:
        if stmt.is_delete or stmt.is_update:
            return QueryFilterApplier.apply_modification_filters(
                stmt, current_model, query._filters, OPERATORS
            )

        return QueryFilterApplier.apply_context_filters(stmt, current_model, query._filters, OPERATORS)

    @staticmethod
    async def delete(query: Any) -> int:
        current_model = query._get_current_model()
        delete_q = delete(current_model)

        if query._filters:
            delete_q = MutationQueryExecutor._apply_filters(query, current_model, delete_q)

        res = await query._repo._execute_modification(delete_q)
        await query._repo._session.flush()
        return res.rowcount
