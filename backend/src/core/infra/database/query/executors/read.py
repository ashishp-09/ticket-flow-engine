from typing import Any, Optional

from sqlalchemy import exists, func, select


class ReadQueryExecutor:
    @staticmethod
    def _extract_annotated_models(rows: list[Any], annotations: dict[str, Any]) -> list[Any]:
        if not rows:
            return []

        first_row = rows[0]
        is_row_tuple = hasattr(first_row, "_mapping") or isinstance(first_row, (tuple, list))

        if not annotations:
            if is_row_tuple:
                return [row[0] for row in rows]
            return rows

        items = []
        for row in rows:
            model_instance = row[0] if is_row_tuple else row
            for name in annotations:
                setattr(model_instance, name, getattr(row._mapping, name, None))
            items.append(model_instance)
        return items

    @staticmethod
    async def get(query: Any, **kwargs: Any) -> Any:
        clone = query.filter(**kwargs) if kwargs else query
        q, modifiers = await clone._execute()
        res = await clone._repo._session.execute(q)

        if not hasattr(clone, "_target_model") and not clone._annotations:
            rows = res.unique().scalars().all()
        else:
            rows = res.unique().all()

        if not rows:
            raise ValueError(f"No {clone._get_current_model().__name__} found matching criteria.")
        if len(rows) > 1:
            raise ValueError(f"Multiple {clone._get_current_model().__name__} returned matching criteria.")

        if not hasattr(clone, "_target_model"):
            model_instances = ReadQueryExecutor._extract_annotated_models(rows, clone._annotations)
            processed = clone._repo._process_results(model_instances[0], modifiers)
            return clone._to_dto(processed)

        return clone._to_dto(rows[0])

    @staticmethod
    async def all(query: Any) -> list[Any]:
        q, modifiers = await query._execute()
        res = await query._repo._session.execute(q)

        if not hasattr(query, "_target_model") and not query._annotations:
            items_raw = res.unique().scalars().all()
            return query._to_dto(query._repo._process_results(items_raw, modifiers))

        rows = res.unique().all()
        if not hasattr(query, "_target_model"):
            items_raw = ReadQueryExecutor._extract_annotated_models(rows, query._annotations)
            return query._to_dto(query._repo._process_results(items_raw, modifiers))

        return query._to_dto(rows)

    @staticmethod
    async def first(query: Any) -> Optional[Any]:
        q, modifiers = await query._execute()
        res = await query._repo._session.execute(q)

        if not hasattr(query, "_target_model") and not query._annotations:
            row = res.unique().scalars().first()
            if not row:
                return None
            return query._to_dto(query._repo._process_results(row, modifiers))

        rows = res.unique().all()
        if not rows:
            return None

        if not hasattr(query, "_target_model"):
            items_raw = ReadQueryExecutor._extract_annotated_models(rows[:1], query._annotations)
            return query._to_dto(query._repo._process_results(items_raw[0], modifiers))

        return query._to_dto(rows[0])

    @staticmethod
    async def paginate(query: Any, offset: int = 0, limit: int = 100) -> tuple[list[Any], int]:
        q, modifiers = await query._execute()

        paginated_q = q.add_columns(func.count().over().label("total_count_over"))
        paginated_q = paginated_q.offset(offset).limit(limit)

        result = await query._repo._session.execute(paginated_q)
        rows = result.unique().all()

        if not rows:
            return [], 0

        total_count = rows[0]._mapping.get("total_count_over", 0)

        if not hasattr(query, "_target_model"):
            items_raw = ReadQueryExecutor._extract_annotated_models(rows, query._annotations)
            processed_items = query._repo._process_results(items_raw, modifiers)
            return query._to_dto(processed_items), total_count

        return query._to_dto(rows), total_count

    @staticmethod
    async def count(query: Any, **kwargs: Any) -> int:
        clone = query.filter(**kwargs) if kwargs else query
        q, _ = await clone._execute()
        count_q = select(func.count()).select_from(q.subquery())
        result = await clone._repo._session.execute(count_q)
        return result.scalar()

    @staticmethod
    async def exists(query: Any, **kwargs: Any) -> bool:
        clone = query.filter(**kwargs) if kwargs else query
        q, _ = await clone._execute()
        exist_q = select(exists(q.subquery()))
        result = await clone._repo._session.execute(exist_q)
        return bool(result.scalar())
