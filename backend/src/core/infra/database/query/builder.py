from typing import Any, Generic, Literal, Optional, overload, Sequence, Type, Union

from sqlalchemy import inspect, select
from sqlalchemy.orm import joinedload, RelationshipProperty, selectinload

from src.core.annotations import DTO_T, ORM_MODEL_T
from .executors import MutationQueryExecutor, ReadQueryExecutor
from .modifiers import BaseQueryModifier


class QueryBuilder(Generic[ORM_MODEL_T, DTO_T]):
    def __init__(self, repo: Any):
        self._repo = repo
        self._filters: dict[str, Any] = {}
        self._order_by: Optional[str] = None
        self._options: list[Any] = []
        self._with_for_update: Union[bool, dict[str, Any]] = False
        self._context_history: list[tuple[Type[Any], Any]] = []
        self._annotations: dict[str, Any] = {}

    def filter(self, **kwargs: Any) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        clone._filters = {**self._filters, **kwargs}
        return clone

    def order_by(self, field: Optional[str]) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        if not field:
            return self
        clone = self._clone()
        clone._order_by = field
        return clone

    def options(self, *args: Any) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        clone._options = [*self._options, *args]
        return clone

    def with_for_update(self, set_val: Union[bool, dict[str, Any]] = True) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        if set_val is True:
            clone._with_for_update = {"of": clone._get_current_model()}
        else:
            clone._with_for_update = set_val
        return clone

    def annotate(self, **kwargs: Any) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        clone._annotations = {**self._annotations, **kwargs}
        return clone

    def _get_current_model(self) -> Type[Any]:
        return self.__dict__.get("_target_model", self._repo.model)

    def _clone(self) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = QueryBuilder(self._repo)
        clone._filters = {**self._filters}
        clone._order_by = self._order_by
        clone._options = [*self._options]
        clone._with_for_update = self._with_for_update
        clone._context_history = [*self._context_history]
        clone._annotations = {**self._annotations}

        if "_target_model" in self.__dict__:
            clone._target_model = self._target_model
            clone._prop_meta = self._prop_meta
        return clone

    def _to_dto(self, items: Any) -> Any:
        return self._repo._to_dto(items)

    async def _execute(self) -> tuple[Any, list[BaseQueryModifier]]:
        current_model = self._get_current_model()
        if not hasattr(self, "_target_model"):
            q, modifiers = self._repo._prepare_query(
                options=self._options,
                with_for_update=self._with_for_update,
                order_by=self._order_by,
                annotations=getattr(self, "_annotations", None),
                **self._filters
            )
        else:
            q = select(current_model)
            if self._filters:
                q = self._repo._build_filtered_query(q, self._filters, getattr(self, "_annotations", None))
            if self._order_by:
                q = self._repo._apply_sorting(q, self._order_by)
            q = self._build_final_criteria(q)
            modifiers = []

        return q, modifiers

    def __getattr__(self, name: str) -> "QueryBuilder[Any, Any]":
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

        current_model = self._get_current_model()
        if not hasattr(current_model, name):
            raise AttributeError(f"'{current_model.__name__}' object has no attribute '{name}'")

        attr = getattr(current_model, name)
        try:
            prop = inspect(attr).property
            if not isinstance(prop, RelationshipProperty):
                raise AttributeError()
        except Exception:
            raise AttributeError(f"'{current_model.__name__}' attribute '{name}' is not a relationship")

        target_model = prop.mapper.class_
        clone = self._clone()

        q, _ = clone._repo._prepare_query(
            options=clone._options,
            with_for_update=clone._with_for_update,
            order_by=clone._order_by,
            **clone._filters
        )

        clone._context_history.append((current_model, q))
        clone._target_model = target_model
        clone._prop_meta = prop

        clone._filters = {}
        clone._order_by = None
        clone._options = []
        clone._with_for_update = False
        clone._annotations = {}
        return clone

    def with_joined(self, *relations: str) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        current_model = clone._get_current_model()
        options = []

        for rel in relations:
            parts = rel.split("__")
            model_attr = getattr(current_model, parts[0])
            opt = joinedload(model_attr)
            prop = inspect(model_attr).property

            for part in parts[1:]:
                parent_model = prop.mapper.class_
                next_attr = getattr(parent_model, part)
                opt = opt.joinedload(next_attr)
                prop = inspect(next_attr).property

            options.append(opt)

        clone._options = [*self._options, *options]
        return clone

    def with_selectin(self, *relations: str) -> "QueryBuilder[ORM_MODEL_T, DTO_T]":
        clone = self._clone()
        current_model = clone._get_current_model()
        options = []

        for rel in relations:
            parts = rel.split("__")
            model_attr = getattr(current_model, parts[0])
            opt = selectinload(model_attr)
            parent_model = current_model

            for part in parts[1:]:
                prop = inspect(getattr(parent_model, parts[0])).property
                parent_model = prop.mapper.class_
                next_attr = getattr(parent_model, part)
                opt = opt.joinedload(next_attr)

            options.append(opt)

        clone._options = [*self._options, *options]
        return clone

    async def get(self, **kwargs: Any) -> Any:
        return await ReadQueryExecutor.get(self, **kwargs)

    async def all(self) -> list[Any]:
        return await ReadQueryExecutor.all(self)

    async def first(self) -> Optional[Any]:
        return await ReadQueryExecutor.first(self)

    async def paginate(self, offset: int = 0, limit: int = 100) -> tuple[list[Any], int]:
        return await ReadQueryExecutor.paginate(self, offset, limit)

    async def count(self, **kwargs: Any) -> int:
        return await ReadQueryExecutor.count(self, **kwargs)

    async def exists(self, **kwargs: Any) -> bool:
        return await ReadQueryExecutor.exists(self, **kwargs)

    @overload
    async def create(
            self,
            m_data: list[dict[str, Any]],
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Literal[False]
    ) -> int:
        ...

    @overload
    async def create(
            self,
            m_data: list[dict[str, Any]],
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Union[Literal[True], Sequence[Any]] = True
    ) -> list[DTO_T]:
        ...

    @overload
    async def create(
            self,
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Literal[False],
            **kwargs: Any
    ) -> int:
        ...

    @overload
    async def create(
            self,
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Union[Literal[True], Sequence[Any]] = True,
            **kwargs: Any
    ) -> Optional[DTO_T]:
        ...

    async def create(
            self,
            m_data: Optional[list[dict[str, Any]]] = None,
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Union[bool, Sequence[Any]] = True,
            **kwargs: Any
    ) -> Any:
        if m_data is not None:
            return await MutationQueryExecutor.create(
                self,
                m_data,
                on_conflict_do_nothing=on_conflict_do_nothing,
                index_elements=index_elements,
                returning=returning
            )
        return await MutationQueryExecutor.create(
            self,
            on_conflict_do_nothing=on_conflict_do_nothing,
            index_elements=index_elements,
            returning=returning,
            **kwargs
        )

    @overload
    async def update(self, *, returning: Literal[True] = True, **kwargs: Any) -> Optional[DTO_T]:
        ...

    @overload
    async def update(self, *, returning: Literal[False], **kwargs: Any) -> int:
        ...

    @overload
    async def update(self, *, returning: Sequence[Any], **kwargs: Any) -> list[Any]:
        ...

    async def update(self, returning: Union[bool, Sequence[Any]] = True, **kwargs: Any) -> Any:
        return await MutationQueryExecutor.update(self, returning=returning, **kwargs)

    async def delete(self) -> int:
        return await MutationQueryExecutor.delete(self)
