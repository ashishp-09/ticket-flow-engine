from typing import Any

from src.app.exceptions import ObjectNotFoundException, ServiceException, WrongStateException
from src.app.uow import AppUnitOfWork
from src.core.infra.transport.http import PaginatedResponseSchema
from src.domain.services.base import GenericService
from src.modules.event.models import EventStatus
from .data_objects import TicketCategoryDTO
from .models import TicketStatus
from .schemas import (
    TicketCategoryCreateSchema,
    TicketCategoryResponseSchema,
    TicketCategoryUpdateSchema,
    TicketCheckInResponseSchema,
    TicketDetailResponseSchema,
    TicketResponseSchema,
    TicketTransferResponseSchema,
)


class TicketService(GenericService[AppUnitOfWork]):
    async def get_all_by_user_id(
            self,
            user_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[TicketResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.ticket
                .filter(order_item__order__user_id=user_id, **(filters or {}))
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=TicketResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )

    async def get_all_by_event_id(
            self,
            user_id: int,
            event_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[TicketResponseSchema]:
        async with self.uow.as_readonly():
            event_obj = await self.uow.event.get(id=event_id)
            if not event_obj or event_obj.user_id != user_id:
                raise ObjectNotFoundException(
                    table=self.uow.event.get_model_name(),
                    value=event_id,
                )

            items, count = await (
                self.uow.ticket
                .filter(category__event_id=event_id, **(filters or {}))
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=TicketResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )

    async def get_by_id(self, ticket_id: int, user_id: int) -> TicketDetailResponseSchema:
        async with self.uow.as_readonly():
            ticket = await (
                self.uow.ticket
                .with_joined("category__event", "order_item__order")
                .get(id=ticket_id)
            )
            if not ticket:
                raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            is_owner = ticket.order_item and ticket.order_item.order and ticket.order_item.order.user_id == user_id
            is_organizer = ticket.category and ticket.category.event and ticket.category.event.user_id == user_id

            if not (is_owner or is_organizer):
                raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            event = ticket.category.event if ticket.category else None

            return TicketDetailResponseSchema(
                id=ticket.id,
                category_id=ticket.category_id,
                status=ticket.status,
                event_id=event.id if event else None,
                event_title=event.title if event else None,
                category_name=ticket.category.name if ticket.category else None,
                price=ticket.category.price if ticket.category else None,
            )

    async def check_in(self, ticket_id: int, user_id: int, is_staff: bool = False) -> TicketCheckInResponseSchema:
        async with self.uow:
            ticket = await (
                self.uow.ticket
                .with_joined("category__event")
                .get(id=ticket_id)
            )
            if not ticket:
                raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            if not is_staff:
                if not (ticket.category and ticket.category.event and ticket.category.event.user_id == user_id):
                    raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            if ticket.status == TicketStatus.CHECKED_IN:
                raise ServiceException("Ticket has already been checked in.")

            if ticket.status != TicketStatus.PAID:
                raise WrongStateException(expected=TicketStatus.PAID, current=ticket.status)

            await (
                self.uow.ticket
                .filter(id=ticket_id)
                .update(status=TicketStatus.CHECKED_IN, returning=False)
            )
            await self.uow.commit()

        return TicketCheckInResponseSchema(
            ticket_id=ticket_id,
            status=TicketStatus.CHECKED_IN,
            message="Ticket successfully validated and checked in.",
        )

    async def transfer(self, ticket_id: int, user_id: int, target_email: str) -> TicketTransferResponseSchema:
        async with self.uow:
            ticket = await (
                self.uow.ticket
                .with_joined("order_item__order")
                .get(id=ticket_id)
            )
            if not ticket:
                raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            if not (ticket.order_item and ticket.order_item.order and ticket.order_item.order.user_id == user_id):
                raise ObjectNotFoundException(table=self.uow.ticket.get_model_name(), value=ticket_id)

            if ticket.status != TicketStatus.PAID:
                raise WrongStateException(expected=TicketStatus.PAID, current=ticket.status)

            target_user = await self.uow.user.get(email=target_email)
            if not target_user:
                raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=target_email)

            # Create new order & order_item for the target user
            target_order = await self.uow.order.create(
                user_id=target_user.id,
                status="paid",
            )
            target_order_item = await self.uow.order_item.filter(order_id=target_order.id).create([{
                "category_id": ticket.category_id,
                "quantity": 1,
                "purchase_price": ticket.order_item.purchase_price if ticket.order_item else 0.0,
            }])

            new_order_item_id = target_order_item[0].id if target_order_item else None
            await (
                self.uow.ticket
                .filter(id=ticket_id)
                .update(order_item_id=new_order_item_id, returning=False)
            )

            await self.uow.commit()

        return TicketTransferResponseSchema(
            ticket_id=ticket_id,
            target_email=target_email,
            message="Ticket transferred successfully.",
        )


class TicketCategoryService(GenericService[AppUnitOfWork]):
    async def create(self, user_id: int, data: TicketCategoryCreateSchema) -> TicketCategoryResponseSchema:
        async with self.uow:
            event_obj = await self.uow.event.get(id=data.event_id)

            if event_obj is None or event_obj.user_id != user_id:
                raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=data.event_id)

            if event_obj.status != EventStatus.DRAFT:
                raise WrongStateException(expected=EventStatus.DRAFT, current=event_obj.status)

            category_obj = await self.uow.ticket_category.create(**data.model_dump())

            await self.uow.commit()

        return TicketCategoryResponseSchema.model_validate(category_obj)

    async def _validate_modification(self, user_id: int, obj_id: int) -> TicketCategoryDTO:
        category_obj = await self.uow.ticket_category.get(id=obj_id)
        if category_obj is None:
            raise ObjectNotFoundException(table=self.uow.ticket_category.get_model_name(), value=obj_id)

        event_obj = await self.uow.event.get(id=category_obj.event_id)
        if event_obj is None or event_obj.user_id != user_id:
            raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=category_obj.event_id)

        if event_obj.status != EventStatus.DRAFT:
            raise WrongStateException(expected=EventStatus.DRAFT, current=event_obj.status)

        return category_obj

    async def update(self, user_id: int, obj_id: int, data: TicketCategoryUpdateSchema) -> bool:
        async with self.uow:
            await self._validate_modification(user_id=user_id, obj_id=obj_id)

            await (
                self.uow.ticket_category
                .filter(id=obj_id)
                .update(**data.model_dump(exclude_unset=True))
            )

            await self.uow.commit()

        return True

    async def delete(self, user_id: int, obj_id: int) -> bool:
        async with self.uow:
            await self._validate_modification(user_id=user_id, obj_id=obj_id)

            await self.uow.ticket_category.filter(id=obj_id).delete()

            await self.uow.commit()

        return True

    async def get_all_by_event_id_public(
            self,
            event_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[TicketCategoryResponseSchema]:
        async with self.uow.as_readonly():
            query_filters = (filters or {}) | {"event_id": event_id, "event__status": EventStatus.UPCOMING}

            items, count = await (
                self.uow.ticket_category
                .filter(**query_filters)
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

            if count == 0:
                event_exists = await self.uow.event.exists(id=event_id, status=EventStatus.UPCOMING)
                if not event_exists:
                    raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=event_id)

        return self._paginate(
            schema=TicketCategoryResponseSchema,
            items=items,
            total_items=count,
            limit=limit
        )

    async def get_all_by_event_id(
            self,
            event_id: int,
            user_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[TicketCategoryResponseSchema]:
        async with self.uow.as_readonly():
            query_filters = (filters or {}) | {"event_id": event_id, "event__user_id": user_id}

            items, count = await (
                self.uow.ticket_category
                .filter(**query_filters)
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

            if count == 0:
                event_exists = await self.uow.event.filter(id=event_id, user_id=user_id).exists()
                if not event_exists:
                    raise ObjectNotFoundException(table=self.uow.event.get_model_name(), value=event_id)

        return self._paginate(
            schema=TicketCategoryResponseSchema,
            items=items,
            total_items=count,
            limit=limit
        )
