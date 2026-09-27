from fastapi import APIRouter, status
from starlette.requests import Request

from src.core.infra.transport.http import cached_endpoint, CacheTag, PaginatedResponseSchema
from src.core.infra.transport.http.annotations import Int32Path
from src.modules.ticket.dependencies import TicketsByEventFiltersDep, TicketServiceDep
from src.modules.ticket.schemas import TicketResponseSchema
from src.modules.user.dependencies import VerifiedUserIdDep
from src.modules.views.dependencies import VisitorDataDep
from src.modules.views.schemas import RegisterViewsRequestSchema
from .dependencies import (
    EventCategoryFiltersDep,
    EventsByUserFiltersDep,
    EventServiceDep,
    UpcomingEventsFiltersDep,
)
from .schemas import (
    EventCategoryResponseSchema,
    EventCreateSchema,
    EventResponseSchema,
    EventUpdateSchema,
)

event_router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@event_router.get("/categories", status_code=status.HTTP_200_OK)
@cached_endpoint(tags=[CacheTag.EVENT_CATEGORIES])
async def get_categories(
        request: Request,
        service: EventServiceDep,
        filters: EventCategoryFiltersDep,
) -> PaginatedResponseSchema[EventCategoryResponseSchema]:
    return await service.get_categories(
        offset=filters.offset, limit=filters.limit, order_by=filters.order_by, filters=filters.specific_filters
    )


@event_router.get("/my", status_code=status.HTTP_200_OK)
async def get_all_private(
        service: EventServiceDep,
        user_id: VerifiedUserIdDep,
        filters: EventsByUserFiltersDep,
) -> PaginatedResponseSchema[EventResponseSchema]:
    return await service.get_all_by_user_id(
        user_id=user_id,
        offset=filters.offset,
        limit=filters.limit,
        order_by=filters.order_by,
        filters=filters.specific_filters,
    )


@event_router.post("/views", status_code=status.HTTP_202_ACCEPTED)
async def increment_views(
        body: RegisterViewsRequestSchema,
        service: EventServiceDep,
        visitor_data: VisitorDataDep,
) -> None:
    await service.increment_views(
        obj_id=body.object_ids,
        visitor_data=visitor_data
    )


@event_router.get("/my/{event_id}", status_code=status.HTTP_200_OK)
async def get_private(
        service: EventServiceDep,
        event_id: Int32Path,
        user_id: VerifiedUserIdDep,
) -> EventResponseSchema:
    return await service.get(obj_id=event_id, user_id=user_id)


@event_router.get("/{event_id}/tickets", status_code=status.HTTP_200_OK)
async def get_tickets(
        event_id: Int32Path,
        service: TicketServiceDep,
        user_id: VerifiedUserIdDep,
        filters: TicketsByEventFiltersDep,
) -> PaginatedResponseSchema[TicketResponseSchema]:
    return await service.get_all_by_event_id(
        user_id=user_id,
        event_id=event_id,
        offset=filters.offset,
        limit=filters.limit,
        order_by=filters.order_by,
        filters=filters.specific_filters,
    )


@event_router.get("/{event_id}", status_code=status.HTTP_200_OK)
async def get_public(service: EventServiceDep, event_id: Int32Path) -> EventResponseSchema:
    return await service.get_public(obj_id=event_id)


@event_router.patch("/{event_id}/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish(service: EventServiceDep, event_id: Int32Path, user_id: VerifiedUserIdDep) -> None:
    await service.publish(event_id=event_id, user_id=user_id)


@event_router.patch("/{event_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel(service: EventServiceDep, event_id: Int32Path, user_id: VerifiedUserIdDep) -> None:
    await service.cancel(event_id=event_id, user_id=user_id)


@event_router.patch("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update(
        service: EventServiceDep,
        event_id: Int32Path,
        user_id: VerifiedUserIdDep,
        body: EventUpdateSchema,
) -> None:
    await service.update(event_id=event_id, user_id=user_id, data=body)


@event_router.post("", status_code=status.HTTP_201_CREATED)
async def create(service: EventServiceDep, body: EventCreateSchema, user_id: VerifiedUserIdDep) -> EventResponseSchema:
    return await service.create(data=body, user_id=user_id)


@event_router.get("", status_code=status.HTTP_200_OK)
@cached_endpoint(tags=CacheTag.UPCOMING_EVENTS)
async def get_all_public(
        request: Request,
        service: EventServiceDep,
        filters: UpcomingEventsFiltersDep,
) -> PaginatedResponseSchema[EventResponseSchema]:
    return await service.get_all_public(
        offset=filters.offset,
        limit=filters.limit,
        order_by=filters.order_by,
        filters=filters.specific_filters
    )
