from typing import Any, Generic, Sequence, Type

from sqlalchemy import asc, desc, select

from src.core.annotations import ORM_MODEL_T
from .filters import QueryFilterApplier
from .modifiers import BaseQueryModifier
from .operators import OPERATORS


class QueryPreparer(Generic[ORM_MODEL_T]):
    model: Type[ORM_MODEL_T]

    def _prepare_query(
            self,
            *,
            order_by: str | None = None,
            options: Sequence[Any] | None = None,
            with_for_update: bool | dict[str, Any] = False,
            annotations: dict[str, Any] | None = None,
            **kwargs: Any,
    ) -> tuple[Any, list[BaseQueryModifier]]:
        q = select(self.model)
        orm_options = []
        modifiers: list[BaseQueryModifier] = []

        if options is not None:
            for opt in options:
                if isinstance(opt, BaseQueryModifier):
                    modifiers.append(opt)
                else:
                    orm_options.append(opt)

        if orm_options:
            q = q.options(*orm_options)

        for modifier in modifiers:
            q = modifier.apply_to_query(q, self.model)

        if with_for_update:
            if isinstance(with_for_update, dict):
                q = q.with_for_update(**with_for_update)
            else:
                q = q.with_for_update()

        if kwargs:
            q = self._build_filtered_query(q, kwargs, annotations)

        if order_by:
            q = self._apply_sorting(q, order_by)

        return q, modifiers

    def _build_filtered_query(self, query: Any, filters: dict[str, Any],
                              annotations: dict[str, Any] | None = None) -> Any:
        return QueryFilterApplier.apply_context_filters(query, self.model, filters, OPERATORS, annotations)

    def _process_results(self, rows: Sequence[Any], modifiers: list[BaseQueryModifier]) -> Any:
        if not rows:
            return rows
        is_sequence = isinstance(rows, (list, tuple, Sequence)) and not (
                isinstance(rows, tuple) and hasattr(rows, "_mapping"))
        instances = list(rows) if is_sequence else [rows]

        if modifiers:
            for modifier in modifiers:
                modifier.process_results(instances, self.model)

        cleaned = [row if isinstance(row, tuple) and len(row) > 0 else row for row in instances]
        return cleaned if is_sequence else cleaned[0]

    def _apply_sorting(self, query: Any, order_by: str) -> Any:
        if order_by.startswith("-"):
            field_name = order_by[1:]
            direction = desc
        else:
            field_name = order_by
            direction = asc

        if hasattr(self.model, field_name) or field_name in query.selected_columns:
            column = getattr(self.model, field_name, None) or query.selected_columns[field_name]
            return query.order_by(direction(column))
        raise ValueError(f"Invalid sort field '{field_name}' for model {self.model.__name__}")
