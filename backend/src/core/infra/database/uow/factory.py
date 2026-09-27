from typing import Callable, Type

from src.core.annotations import SERVICE_T, UOW_T
from src.core.infra.cache.managers import AbstractCacheManager
from src.core.infra.tasks.managers import AbstractTaskManager
from src.core.infra.transport.queue.producers.abstract import AbstractQueueProducer


class ServiceFactory:
    def __init__(
            self,
            service_cls: Type[SERVICE_T],
            uow_factory: Callable[[], UOW_T],
            tasks_factory: Callable[[], AbstractTaskManager],
            cache_factory: Callable[[], AbstractCacheManager],
            queue_producer_factory: Callable[[], AbstractQueueProducer],
    ):
        self.service_cls = service_cls
        self.uow_factory = uow_factory
        self.tasks_factory = tasks_factory
        self.cache_factory = cache_factory
        self.queue_producer_factory = queue_producer_factory

    async def __call__(self) -> SERVICE_T:
        return self.service_cls(
            uow=self.uow_factory(),
            tasks=self.tasks_factory(),
            cache=self.cache_factory(),
            queue=self.queue_producer_factory(),
        )
