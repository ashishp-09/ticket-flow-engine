from fastapi import APIRouter, status
from starlette.requests import Request

from src.core.infra.transport.http import cached_endpoint, CacheTag, PaginatedResponseSchema
from src.modules.user.dependencies import AnyUserIdDep, VerifiedUserIdDep
from .dependencies import TicketCategoryFiltersDep, TicketCategoryServiceDep, TicketServiceDep, TicketsFiltersDep
from .schemas import (
    TicketCategoryCreateSchema,
    TicketCategoryResponseSchema,
    TicketCategoryUpdateSchema,
    TicketCheckInResponseSchema,
    TicketDetailResponseSchema,
    TicketResponseSchema,
    TicketTransferResponseSchema,
    TicketTransferSchema,
)

ticket_router = APIRouter(
    prefix="/tickets",
    tags=["tickets"],
    responses={404: {"description": "Not found"}},
)


@ticket_router.get("/my", status_code=status.HTTP_200_OK)
async def get_all_by_current_user(
        service: TicketServiceDep, user_id: AnyUserIdDep, filters: TicketsFiltersDep
) -> PaginatedResponseSchema[TicketResponseSchema]:
    return await service.get_all_by_user_id(
        user_id=user_id,
        offset=filters.offset,
        limit=filters.limit,
        order_by=filters.order_by,
        filters=filters.specific_filters,
    )


@ticket_router.get("/{ticket_id}", status_code=status.HTTP_200_OK)
async def get_ticket(
        service: TicketServiceDep, user_id: AnyUserIdDep, ticket_id: int
) -> TicketDetailResponseSchema:
    return await service.get_by_id(ticket_id=ticket_id, user_id=user_id)


@ticket_router.post("/{ticket_id}/check-in", status_code=status.HTTP_200_OK)
async def check_in_ticket(
        service: TicketServiceDep, user_id: AnyUserIdDep, ticket_id: int
) -> TicketCheckInResponseSchema:
    return await service.check_in(ticket_id=ticket_id, user_id=user_id)


@ticket_router.post("/{ticket_id}/transfer", status_code=status.HTTP_200_OK)
async def transfer_ticket(
        service: TicketServiceDep, user_id: AnyUserIdDep, ticket_id: int, body: TicketTransferSchema
) -> TicketTransferResponseSchema:
    return await service.transfer(ticket_id=ticket_id, user_id=user_id, target_email=body.target_email)


category_router = APIRouter(
    prefix="/categories",
    responses={404: {"description": "Not found"}},
)


@category_router.get("/{event_id}", status_code=status.HTTP_200_OK)
@cached_endpoint(tags=[CacheTag.CATEGORIES_BY_EVENT_ID])
async def get_by_event_id(
        request: Request,
        service: TicketCategoryServiceDep,
        event_id: int,
        filters: TicketCategoryFiltersDep
) -> PaginatedResponseSchema[TicketCategoryResponseSchema]:
    return await service.get_all_by_event_id_public(
        event_id=event_id,
        offset=filters.offset,
        limit=filters.limit,
        order_by=filters.order_by,
        filters=filters.specific_filters,
    )


@category_router.post("", status_code=status.HTTP_201_CREATED)
async def create_ticket_category(
        service: TicketCategoryServiceDep,
        body: TicketCategoryCreateSchema,
        user_id: VerifiedUserIdDep
) -> TicketCategoryResponseSchema:
    return await service.create(user_id=user_id, data=body)


@category_router.patch("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_ticket_category(
        service: TicketCategoryServiceDep,
        body: TicketCategoryUpdateSchema,
        user_id: VerifiedUserIdDep,
        category_id: int
):
    await service.update(user_id=user_id, obj_id=category_id, data=body)


@category_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket_category(
        service: TicketCategoryServiceDep,
        user_id: VerifiedUserIdDep,
        category_id: int
):
    await service.delete(user_id=user_id, obj_id=category_id)


ticket_router.include_router(category_router)
