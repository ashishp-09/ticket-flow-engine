from typing import Any

from src.app.exceptions import ObjectNotFoundException, ServiceException, UniqueFieldException, WrongStateException
from src.app.uow import AppUnitOfWork
from src.core.infra.database.exceptions import UniqueViolationError
from src.core.infra.database.query import Case, When
from src.core.infra.transport.http import PaginatedResponseSchema
from src.domain.services.base import GenericService
from src.modules.views.mixins import ViewableServiceMixin
from .exceptions import EventCategoryHasEventsException, EventCategoryIsNotALeafException
from .models import EventState, EventStatus
from .schemas import (
    EventCategoryCreateSchema,
    EventCategoryResponseSchema,
    EventCreateSchema,
    EventResponseSchema, EventUpdateSchema,
)


class EventService(GenericService[AppUnitOfWork], ViewableServiceMixin):
    def _get_model_name(self) -> str:
        return self.uow.event.get_model_name()

    async def create(
            self,
            data: EventCreateSchema,
            user_id: int,
    ) -> EventResponseSchema:
        async with self.uow:
            is_leaf_category = await (
                self.uow.event_category
                .filter(id=data.category_id, children__has_no=True)
                .exists()
            )

            if not is_leaf_category:
                category_exists = await self.uow.event_category.exists(id=data.category_id)

                if not category_exists:
                    raise ObjectNotFoundException(
                        table=self.uow.event_category.get_model_name(),
                        value=data.category_id,
                    )

                raise EventCategoryIsNotALeafException(obj_id=data.category_id)

            event_dto = await self.uow.event.create(user_id=user_id, **data.model_dump())

            await self.uow.commit()

        return EventResponseSchema.model_validate(event_dto)

    async def create_category(self, data: EventCategoryCreateSchema) -> EventCategoryResponseSchema:
        async with self.uow:
            if data.parent_id is not None:
                parent_obj_exists = await self.uow.event_category.exists(id=data.parent_id)

                if not parent_obj_exists:
                    raise ObjectNotFoundException(
                        table=self.uow.event_category.get_model_name(),
                        value=data.parent_id,
                    )

                has_events = await self.uow.event.exists(category_id=data.parent_id)
                if has_events:
                    raise EventCategoryHasEventsException(obj_id=data.parent_id)

            try:
                category_obj = await self.uow.event_category.create(**data.model_dump())
            except UniqueViolationError:
                raise UniqueFieldException(field="name", value=data.name)

            if not category_obj:
                raise ServiceException("Unable to create event category.")

            await self.uow.commit()

        return EventCategoryResponseSchema.model_validate(category_obj)

    async def publish(
            self,
            user_id: int,
            event_id: int,
    ) -> bool:
        async with self.uow:
            is_published = await (
                self.uow.event
                .filter(id=event_id, user_id=user_id, state=EventState.DRAFT)
                .update(state=EventState.ON_MODERATION)
            )

            if not is_published:
                event_obj = await self.uow.event.get(id=event_id, user_id=user_id)
                if not event_obj:
                    raise ObjectNotFoundException(
                        table=self.uow.event.get_model_name(),
                        value=event_id,
                    )

                if event_obj.state == EventState.ON_MODERATION:
                    return True

                raise WrongStateException(
                    expected=EventState.DRAFT,
                    current=event_obj.state,
                )

            await self.uow.commit()

        return True

    async def update(
            self,
            data: EventUpdateSchema,
            user_id: int,
            event_id: int,
    ) -> bool:
        async with self.uow:
            obj = await (
                self.uow.event
                .filter(id=event_id, user_id=user_id, state=EventState.DRAFT)
                .update(**data.model_dump(exclude_unset=True))
            )

            if not obj:
                is_exists = await self.uow.event.filter(id=event_id, user_id=user_id).exists()
                if not is_exists:
                    raise ObjectNotFoundException(
                        table=self.uow.event.get_model_name(),
                        value=event_id,
                    )
                raise WrongStateException(expected=EventState.DRAFT)

            await self.uow.commit()

        return True

    async def cancel(
            self,
            event_id: int,
            user_id: int,
    ) -> bool:
        async with self.uow:
            is_canceled = await (
                self.uow.event
                .filter(
                    id=event_id,
                    user_id=user_id,
                    state__in=[EventState.DRAFT, EventState.ON_MODERATION]
                )
                .update(state=EventState.CANCELLED)
            )
            if not is_canceled:
                event_obj = await self.uow.event.get(id=event_id, user_id=user_id)
                if not event_obj:
                    raise ObjectNotFoundException(
                        table=self.uow.event.get_model_name(),
                        value=event_id,
                    )

                if event_obj.state == EventState.CANCELLED:
                    return True

                raise WrongStateException(
                    expected=[EventState.DRAFT, EventState.ON_MODERATION],
                    current=event_obj.state
                )
            await self.uow.commit()
        return True

    async def moderate(self, event_id: int, result: bool) -> bool:
        async with self.uow:
            target_state = EventState.APPROVED if result else EventState.REJECTED

            is_moderated = await (
                self.uow.event
                .filter(id=event_id, state=EventState.ON_MODERATION)
                .update(state=target_state)
            )

            if not is_moderated:
                event_obj = await self.uow.event.get(id=event_id)
                if not event_obj:
                    raise ObjectNotFoundException(
                        table=self.uow.event.get_model_name(),
                        value=event_id,
                    )

                if event_obj.state == target_state:
                    return True

                raise WrongStateException(
                    expected=EventState.ON_MODERATION,
                    current=event_obj.state,
                )
            await self.uow.commit()
        return True

    async def get_for_moderation(
            self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100,
            order_by: str | None = None
    ) -> PaginatedResponseSchema[EventResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.event
                .filter(state=EventState.ON_MODERATION, **(filters or {}))
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=EventResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )

    async def get_all_public(
            self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100,
            order_by: str | None = None
    ) -> PaginatedResponseSchema[EventResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.event
                .filter(status=EventStatus.UPCOMING, **(filters or {}))
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=EventResponseSchema,
            items=await self._enrich_with_views(items=items),
            total_items=count,
            limit=limit,
        )

    async def get_public(self, obj_id: int) -> EventResponseSchema:
        async with self.uow.as_readonly():
            obj = await self.uow.event.get(id=obj_id, status=EventStatus.UPCOMING)

            if not obj:
                raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=obj_id)

            obj = await self._enrich_with_views(items=obj)

        return EventResponseSchema.model_validate(obj)

    async def get(self, obj_id: int, user_id: int) -> EventResponseSchema:
        async with self.uow.as_readonly():
            obj = await self.uow.event.get(id=obj_id, user_id=user_id)

            if not obj:
                raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=obj_id)

            obj = await self._enrich_with_views(items=obj)

        return EventResponseSchema.model_validate(obj)

    async def get_all_by_user_id(
            self,
            user_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[EventResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.event
                .filter(user_id=user_id, **(filters or {}))
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=EventResponseSchema,
            items=await self._enrich_with_views(items=items),
            total_items=count,
            limit=limit,
        )

    async def get_categories(
            self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100,
            order_by: str | None = None
    ) -> PaginatedResponseSchema[EventCategoryResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.event_category
                .filter(**(filters or {}))
                .with_selectin("children")
                .order_by(order_by)
                .annotate(
                    can_create_events=Case(
                        When(then=False, children__has_any=True),
                        default=True
                    ),
                    can_create_subcategories=Case(
                        When(then=False, events__has_any=True),
                        default=True
                    )
                )
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=EventCategoryResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )
