from fastapi import APIRouter, Depends, status
from starlette.requests import Request

from src.core.infra.transport.http import cached_endpoint, CacheTag, GenericResultRequestSchema, \
    Int32Path, invalidates_cache, PaginatedResponseSchema
from src.modules.event.dependencies import EventCategoryFiltersDep, EventsByUserFiltersDep, EventServiceDep
from src.modules.event.schemas import EventCategoryCreateSchema, EventCategoryResponseSchema, EventResponseSchema
from src.modules.user.dependencies import AdminUserIdDep, UserFiltersDep, UserServiceDep
from src.modules.user.models import UserRole
from src.modules.user.roles import RoleChecker
from src.modules.user.schemas import UserResponseSchema

moderation_router = APIRouter(
    prefix="/moderation",
    tags=["moderation"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(RoleChecker(required_role=UserRole.MODERATOR))],
)


@moderation_router.get("/events", status_code=status.HTTP_200_OK)
async def get_all_events_up_to_moderation(
        service: EventServiceDep,
        filters: EventsByUserFiltersDep,
) -> PaginatedResponseSchema[EventResponseSchema]:
    return await service.get_for_moderation(
        offset=filters.offset, limit=filters.limit, order_by=filters.order_by, filters=filters.specific_filters
    )


@moderation_router.patch("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
@invalidates_cache(tags=CacheTag.UPCOMING_EVENTS)
async def moderate_event(
        service: EventServiceDep,
        body: GenericResultRequestSchema,
        event_id: Int32Path,
):
    await service.moderate(event_id=event_id, result=body.result)


@moderation_router.get("/users", status_code=status.HTTP_200_OK)
async def get_all_users_up_to_verification(
        service: UserServiceDep,
        filters: UserFiltersDep,
) -> PaginatedResponseSchema[UserResponseSchema]:
    return await service.get_for_verification(
        offset=filters.offset, limit=filters.limit, order_by=filters.order_by, filters=filters.specific_filters
    )


@moderation_router.patch("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def moderate_user(
        service: UserServiceDep,
        body: GenericResultRequestSchema,
        user_id: Int32Path,
) -> None:
    await service.verify(user_id=user_id, result=body.result)


admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(RoleChecker(required_role=UserRole.ADMIN))],
)


@admin_router.post("/categories", status_code=status.HTTP_201_CREATED)
@invalidates_cache(tags=CacheTag.ADMIN_EVENT_CATEGORIES)
async def create(
        service: EventServiceDep,
        body: EventCategoryCreateSchema,
) -> EventCategoryResponseSchema:
    return await service.create_category(data=body)


@admin_router.get("/categories", status_code=status.HTTP_200_OK)
@cached_endpoint(tags=CacheTag.ADMIN_EVENT_CATEGORIES)
async def get_all_categories(
        request: Request,
        service: EventServiceDep,
        filters: EventCategoryFiltersDep,
) -> PaginatedResponseSchema[EventCategoryResponseSchema]:
    return await service.get_categories(
        offset=filters.offset, limit=filters.limit, order_by=filters.order_by, filters=filters.specific_filters
    )


@admin_router.get("/users", status_code=status.HTTP_200_OK)
async def get_all_users(
        service: UserServiceDep,
        filters: UserFiltersDep,
) -> PaginatedResponseSchema[UserResponseSchema]:
    return await service.get_all(
        offset=filters.offset, limit=filters.limit, order_by=filters.order_by, filters=filters.specific_filters
    )


@admin_router.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(service: UserServiceDep, user_id: Int32Path) -> UserResponseSchema:
    return await service.get(user_id=user_id)


@admin_router.patch("/users/{user_id}/ban", status_code=status.HTTP_204_NO_CONTENT)
async def ban_user(service: UserServiceDep, user_id: Int32Path, actor_id: AdminUserIdDep) -> None:
    await service.ban(user_id=user_id, actor_id=actor_id)


@admin_router.patch("/users/{user_id}/unban", status_code=status.HTTP_204_NO_CONTENT)
async def unban_user(service: UserServiceDep, user_id: Int32Path, actor_id: AdminUserIdDep) -> None:
    await service.unban(user_id=user_id, actor_id=actor_id)
