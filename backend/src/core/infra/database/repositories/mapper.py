from dataclasses import fields
from typing import Generic, Sequence, Type, overload

from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import hybrid_property

from src.core.annotations import ORM_MODEL_T, DTO_T


class RepositoryMapper(Generic[ORM_MODEL_T, DTO_T]):
    model: Type[ORM_MODEL_T]
    dto: Type[DTO_T]

    @overload
    def _to_dto(self, obj_orm: ORM_MODEL_T) -> DTO_T:
        ...

    @overload
    def _to_dto(self, obj_orm: Sequence[ORM_MODEL_T]) -> list[DTO_T]:
        ...

    def _to_dto(self, obj_orm: ORM_MODEL_T | Sequence[ORM_MODEL_T]) -> DTO_T | list[DTO_T]:
        if not obj_orm:
            return [] if isinstance(obj_orm, (list, tuple, Sequence)) else None

        is_sequence = isinstance(obj_orm, (list, tuple, Sequence))
        instances = list(obj_orm) if is_sequence else [obj_orm]

        allowed_fields = {f.name for f in fields(self.dto)}
        first_instance = instances[0]
        if isinstance(first_instance, tuple) and len(first_instance) > 0:
            first_instance = first_instance[0]

        first_insp = inspect(first_instance)
        mapper = first_insp.mapper if hasattr(first_insp, "mapper") else first_insp

        hybrid_fields = {attr.__name__ for attr in mapper.all_orm_descriptors if isinstance(attr, hybrid_property)}
        relationships = mapper.relationships

        items_dto = []
        for instance in instances:
            actual_instance = instance if isinstance(instance, tuple) and len(instance) > 0 else instance
            if not actual_instance:
                continue

            obj_insp = inspect(actual_instance)
            loaded_data = {}

            for f in allowed_fields:
                if f in relationships:
                    if f not in obj_insp.unloaded:
                        loaded_data[f] = getattr(actual_instance, f)
                elif hybrid_fields and f in hybrid_fields:
                    loaded_data[f] = getattr(actual_instance, f)
                elif hasattr(actual_instance, f):
                    if f in actual_instance.__dict__ or f not in obj_insp.unloaded:
                        loaded_data[f] = getattr(actual_instance, f)

            items_dto.append(self.dto(**loaded_data))

        return items_dto if is_sequence else items_dto[0]
