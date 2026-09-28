from typing import Annotated

from fastapi import Depends, Query

from src.app.uow import create_app_uow
from src.core.infra.database import get_service_factory
from .schemas import OrderFilterParamsSchema, OrderItemFilterParamsSchema
from .services import OrderService

OrderServiceDep = Annotated[OrderService, Depends(get_service_factory(create_app_uow, OrderService))]

OrderFilterParamsSchemaDep = Annotated[OrderFilterParamsSchema, Query()]
OrderItemFilterParamsSchemaDep = Annotated[OrderItemFilterParamsSchema, Query()]
