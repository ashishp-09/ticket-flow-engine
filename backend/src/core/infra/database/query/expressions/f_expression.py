from typing import Any

from .base import BaseExpression


class F(BaseExpression):
    def __init__(self, path: str):
        self.path = path

    def resolve(self, current_model: Any, operators_map: dict[str, Any] | None = None) -> Any:
        return self._resolve_path_to_expression(current_model, self.path)
