from __future__ import annotations

from typing import Any, Generic, Type, TYPE_CHECKING

from src.core.infra.transport.queue.producers.abstract import AbstractQueueProducer

if TYPE_CHECKING:
    from src.core.infra.database.repositories import GenericRepository

from src.core.annotations import UOW_T
from src.core.infra.transport.http.annotations import PYDANTIC_MODEL_T
from src.core.infra.cache.managers.abstract import AbstractCacheManager
from src.core.infra.transport.http.schemas.pagination import PaginatedResponseSchema
from src.core.infra.tasks.managers.abstract import AbstractTaskManager


class GenericService(Generic[UOW_T]):
    _repo_cls: Type["GenericRepository"]
    _PAGINATED_SCHEMA_CACHE = {}

    def __init__(
            self,
            uow: UOW_T,
            tasks: AbstractTaskManager,
            cache: AbstractCacheManager,
            queue: AbstractQueueProducer
    ):
        self.uow = uow
        self.tasks = tasks
        self.cache = cache
        self.queue = queue

    def __init_subclass__(cls, repo: Type["GenericRepository"] = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if repo is not None:
            cls._repo_cls = repo

    def _paginate_raw(
            self,
            items: list[Any],
            total_items: int,
            limit: int = 10,
    ) -> dict:
        return {
            "count": total_items,
            "max_pages": limit,
            "results": items,
        }

    def _paginate(
            self, schema: Type[PYDANTIC_MODEL_T], items: list[Any], total_items: int, limit: int = 10
    ) -> PaginatedResponseSchema[PYDANTIC_MODEL_T]:
        raw = self._paginate_raw(items, total_items, limit)

        if schema not in self._PAGINATED_SCHEMA_CACHE:
            self._PAGINATED_SCHEMA_CACHE[schema] = PaginatedResponseSchema[schema]

        paginated_cls = self._PAGINATED_SCHEMA_CACHE[schema]
        return paginated_cls(**raw)
