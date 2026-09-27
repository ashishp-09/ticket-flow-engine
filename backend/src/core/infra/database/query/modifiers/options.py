from typing import Any, Sequence

from .base import BaseQueryModifier
from .expressions import SQLFunction


class Annotate(BaseQueryModifier):
    def __init__(self, **kwargs: SQLFunction):
        self.kwargs = kwargs

    def apply_to_query(self, query: Any, current_model: Any) -> Any:
        columns_to_add = []
        for alias, expression in self.kwargs.items():
            subq = expression.resolve(current_model).label(alias)
            columns_to_add.append(subq)
        return query.add_columns(*columns_to_add)

    def process_results(self, rows: Sequence[Any], current_model: Any) -> None:
        if not rows:
            return

        for alias in self.kwargs.keys():
            for row in rows:
                model_instance = row if isinstance(row, tuple) and len(row) > 0 else row
                if model_instance:
                    setattr(model_instance, alias, row._mapping[alias])
