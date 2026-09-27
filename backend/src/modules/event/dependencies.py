from typing import Annotated

from fastapi import Depends, Query

from src.app.uow import create_app_uow
from src.core.infra.database.uow_factory import get_service_factory
from .schemas import (
    EventCategoryFilterParamsSchema,
    EventsByUserFilterParamsSchema,
    UpcomingEventsFilterParamsSchema,
)
from .services import EventService

EventServiceDep = Annotated[EventService, Depends(get_service_factory(create_app_uow, EventService))]

UpcomingEventsFiltersDep = Annotated[UpcomingEventsFilterParamsSchema, Query()]
EventsByUserFiltersDep = Annotated[EventsByUserFilterParamsSchema, Query()]
EventCategoryFiltersDep = Annotated[EventCategoryFilterParamsSchema, Query()]
