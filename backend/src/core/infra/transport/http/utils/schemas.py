from typing import Any, Type

from pydantic import BaseModel

from ..annotations import PYDANTIC_MODEL_T


def partial_model(base_model: Type[BaseModel]):
    def decorator(cls: PYDANTIC_MODEL_T) -> PYDANTIC_MODEL_T:
        for field_name, field_info in base_model.model_fields.items():
            field_info.default = None
            field_info.annotation = Any | None
            cls.model_fields[field_name] = field_info

        cls.model_rebuild(force=True)
        return cls

    return decorator
