from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from src.app.uow import create_app_uow
from src.core.infra.database import get_service_factory
from .data_objects import VisitorData
from .services import ViewLogService


def get_visitor_data(request: Request) -> VisitorData:
    ip_address = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "unknown")
    user_agent = request.headers.get("user-agent", "unknown")
    return VisitorData(ip_address=ip_address, user_agent=user_agent)


VisitorDataDep = Annotated[VisitorData, Depends(get_visitor_data)]

get_view_log_service = get_service_factory(create_app_uow, ViewLogService)

ViewLogServiceDep = Annotated[ViewLogService, Depends(get_view_log_service)]
