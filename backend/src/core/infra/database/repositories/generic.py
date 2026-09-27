from abc import ABC
from typing import Any, Literal, Optional, overload, Sequence, Type, Union

from sqlalchemy import Delete, Insert, Update
from sqlalchemy.exc import DBAPIError, IntegrityError, ResourceClosedError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.annotations import DTO_T, ORM_MODEL_T
from src.core.infra.database.exceptions import DatabaseExceptionMapper
from .mapper import RepositoryMapper
from ..query import ModificationResult, QueryBuilder, QueryPreparer


class GenericRepository(ABC, QueryPreparer[ORM_MODEL_T], RepositoryMapper[ORM_MODEL_T, DTO_T]):
    model: Type[ORM_MODEL_T]
    dto: Type[DTO_T]

    def __init__(self, session: AsyncSession, exception_mapper: DatabaseExceptionMapper):
        self._session = session
        self._exception_mapper = exception_mapper

    def __init_subclass__(cls, model: Type[ORM_MODEL_T] = None, dto: Type[DTO_T] = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if model is not None:
            cls.model = model
        if dto is not None:
            cls.dto = dto

    @classmethod
    def get_model_name(cls):
        return cls.model.__tablename__.lower() if getattr(cls.model, "__tablename__",
                                                          None) else cls.model.__name__.lower()

    def query(self) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return QueryBuilder(self)

    def with_joined(self, *relations: str) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return self.query().with_joined(*relations)

    def with_selectin(self, *relations: str) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return self.query().with_selectin(*relations)

    def filter(self, **kwargs: Any) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return self.query().filter(**kwargs)

    def order_by(self, field: Optional[str]) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return self.query().order_by(field)

    def options(self, *args: Any) -> QueryBuilder[ORM_MODEL_T, DTO_T]:
        return self.query().options(*args)

    async def get(self, **kwargs: Any) -> Optional[DTO_T]:
        try:
            return await self.query().get(**kwargs)
        except ValueError:
            return None

    async def all(self) -> list[DTO_T]:
        return await self.query().all()

    async def first(self) -> Optional[DTO_T]:
        return await self.query().first()

    async def paginate(self, offset: int = 0, limit: int = 100) -> tuple[list[DTO_T], int]:
        return await self.query().paginate(offset=offset, limit=limit)

    async def count(self, **kwargs: Any) -> int:
        return await self.query().count(**kwargs)

    async def exists(self, **kwargs: Any) -> bool:
        return await self.query().exists(**kwargs)

    @overload
    async def create(
            self,
            mappings: list[dict[str, Any]],
            *,
            on_conflict_do_nothing: bool = False,
            index_elements: Optional[list[str]] = None,
            returning: Literal[False]
    ) -> int:
        ...

    @overload
    async def create(
            self,
            mappings: list[dict[str, Any]],
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
            return await self.query().create(
                m_data,
                on_conflict_do_nothing=on_conflict_do_nothing,
                index_elements=index_elements,
                returning=returning
            )

        return await self.query().create(
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
        return await self.query().update(returning=returning, **kwargs)

    async def delete(self) -> int:
        return await self.query().delete()

    async def get_or_create(self, **kwargs: Any) -> tuple[DTO_T, bool]:
        try:
            obj_dto = await self.get(**kwargs)
            return obj_dto, False
        except ValueError:
            try:
                async with self._session.begin_nested():
                    dto = await self.create(**kwargs)
                    if dto is not None:
                        if isinstance(dto, list):
                            dto = dto[0]
                        return dto, True
                    raise ValueError("Failed to create.")
            except (IntegrityError, ValueError):
                obj_dto = await self.get(**kwargs)
                return obj_dto, False

    async def _execute_modification(self, q: Update | Delete | Insert) -> ModificationResult:
        try:
            res = await self._session.execute(q)
        except DBAPIError as exc:
            self._exception_mapper.handle(exc)

        rowcount = getattr(res, "rowcount", 0)

        try:
            returning_rows = list(res.scalars().all())
        except ResourceClosedError:
            returning_rows = []

        if rowcount is None or rowcount == -1:
            rowcount = len(returning_rows)

        return ModificationResult(rowcount=rowcount, returning_rows=returning_rows)
