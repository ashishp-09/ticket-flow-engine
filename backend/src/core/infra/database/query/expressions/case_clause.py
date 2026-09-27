from typing import Any

from sqlalchemy import case

from .base import BaseExpression
from .when_clause import When


class Case(BaseExpression):
    def __init__(self, *whens: When, default: Any = None):
        self.whens = whens
        self.default = default

    def resolve(self, current_model: Any, operators_map: dict[str, Any] | None = None) -> Any:
        whens_list = []

        for when_clause in self.whens:
            condition, then_val = when_clause.resolve(current_model, operators_map)
            whens_list.append((condition, then_val))

        return case(*whens_list, else_=self.default)
