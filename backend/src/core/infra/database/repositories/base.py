import types
from typing import Any

from src.core.annotations import DTO_T, ORM_MODEL_T
from .generic import GenericRepository


class Repository(GenericRepository[ORM_MODEL_T, DTO_T]):
    def __class_getitem__(cls, params: Any) -> Any:
        if not isinstance(params, tuple):
            raise TypeError("Repository configuration must be a tuple: [Model, DTO, ...]")

        model_cls, dto_cls = params[0], params[1]
        repo_class_name = f"{model_cls.__name__}Repository"

        dynamic_repo_cls = types.new_class(
            repo_class_name,
            bases=(GenericRepository[model_cls, dto_cls],),
            kwds={"model": model_cls, "dto": dto_cls}
        )

        return dynamic_repo_cls
