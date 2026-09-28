from typing import Annotated

from fastapi import Depends, Query

from src.app.uow import create_app_uow
from src.core.infra.database import get_service_factory
from .schemas import TicketCategoryFilterParamsSchema, TicketsByEventFilterParamsSchema, TicketsFilterParamsSchema
from .services import TicketCategoryService, TicketService

TicketServiceDep = Annotated[TicketService, Depends(get_service_factory(create_app_uow, TicketService))]
TicketCategoryServiceDep = Annotated[TicketCategoryService, Depends(get_service_factory(create_app_uow, TicketCategoryService))]

TicketsFiltersDep = Annotated[TicketsFilterParamsSchema, Query()]
TicketsByEventFiltersDep = Annotated[TicketsByEventFilterParamsSchema, Query()]
TicketCategoryFiltersDep = Annotated[TicketCategoryFilterParamsSchema, Query()]
