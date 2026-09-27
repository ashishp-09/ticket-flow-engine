from typing import Callable, Type

from src.core.annotations import SERVICE_T
from src.core.infra.cache.factory import get_cache_manager
from src.core.infra.database.uow.factory import ServiceFactory
from src.core.infra.database.uow.units import AbstractUnitOfWork
from src.core.infra.tasks.factory import get_task_manager
from src.core.infra.transport.queue.factory import get_queue_producer


def get_service_factory(
        uow_factory: Callable[..., AbstractUnitOfWork],
        service_cls: Type[SERVICE_T]
) -> ServiceFactory:
    return ServiceFactory(
        service_cls=service_cls,
        uow_factory=uow_factory,
        tasks_factory=get_task_manager,
        cache_factory=get_cache_manager,
        queue_producer_factory=get_queue_producer
    )
