from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import RelationshipProperty


class BaseExpression(ABC):
    @abstractmethod
    def resolve(self, current_model: Any, operators_map: dict[str, Any] | None = None) -> Any:
        pass

    def _resolve_path_to_expression(self, current_model: Any, path: str) -> Any:
        parts = path.split("__")
        target_field = parts.pop()

        if not parts:
            if hasattr(current_model, target_field):
                return getattr(current_model, target_field)
            raise AttributeError(f"Field '{target_field}' not found on model {current_model.__name__}")

        model = current_model
        stmt = None
        last_remote_col = None

        for relation_name in parts:
            if not hasattr(model, relation_name):
                raise AttributeError(f"Could not resolve relation '{relation_name}' on model {model.__name__}")

            relation_attr = getattr(model, relation_name)
            prop = relation_attr.property
            target_model = prop.mapper.class_

            local_col = list(prop.local_columns)[0]
            remote_col = list(prop.remote_side)[0]

            if stmt is None:
                stmt = select(target_model).where(remote_col == local_col)
            else:
                stmt = stmt.join(target_model, remote_col == last_remote_col)

            last_remote_col = remote_col
            model = target_model

        if hasattr(model, target_field):
            attr = getattr(model, target_field)
            try:
                prop = inspect(attr).property
                if isinstance(prop, RelationshipProperty):
                    return attr
            except Exception:
                pass
            return stmt.with_only_columns(attr).scalar_subquery()

        raise AttributeError(f"Field '{target_field}' not found on model {model.__name__}")
