from datetime import datetime, timezone
from typing import Any, Optional

from src.app.exceptions import ObjectNotFoundException, ServiceException, WrongStateException
from src.app.uow import AppUnitOfWork
from src.core.infra.database.query import Case, When
from src.core.infra.payment.factory import get_payment_gateway
from src.core.infra.transport.http import PaginatedResponseSchema
from src.domain.services.base import GenericService
from src.modules.event.data_objects import EventDTO
from src.modules.ticket.data_objects import TicketCategoryDTO
from src.modules.ticket.exceptions import NoTicketsAvailableException
from src.modules.ticket.models import TicketStatus
from src.modules.user.data_objects import UserDTO
from .data_objects import OrderDTO
from .models import OrderStatus
from .schemas import (
    OrderCancelResponseSchema,
    OrderCreateSchema,
    OrderEmailDataSchema,
    OrderEmailItemSchema,
    OrderItemResponseSchema,
    OrderResponseSchema,
    PaymentSessionCreateSchema,
    PaymentSessionResponseSchema,
)


class OrderService(GenericService[AppUnitOfWork]):
    async def create(self, data: OrderCreateSchema, user_id: Optional[int]) -> OrderResponseSchema:
        if not (user_id is None) ^ (data.anonymous_email is None):
            raise ValueError(
                "Exactly one field must be provided: either 'user_id' or 'anonymous_email'"
            )

        category_ids = list({item.category_id for item in data.items})
        requested_quantities = {item.category_id: item.quantity for item in data.items}
        anonymous_email = None if user_id is not None else data.anonymous_email

        async with self.uow:
            categories: list[TicketCategoryDTO] = await (
                self.uow.ticket_category
                .filter(
                    id__in=category_ids,
                    id=Case(
                        *(When(id=cat_id, available_quantity__gte=qty) for cat_id, qty in requested_quantities.items())
                    )
                )
                .with_for_update()
                .all()
            )
            categories_map = {cat.id: cat for cat in categories}

            if len(categories) != len(category_ids):
                for item in data.items:
                    cat = categories_map.get(item.category_id)
                    if not cat:
                        raise NoTicketsAvailableException(
                            obj_id=item.category_id,
                            available=0,
                            requested=item.quantity
                        )

            items_data = [
                {
                    "category_id": item.category_id,
                    "quantity": item.quantity,
                    "purchase_price": categories_map[item.category_id].price
                }
                for item in data.items
            ]

            order_dto = await self.uow.order.create(
                user_id=user_id,
                anonymous_email=anonymous_email,
            )

            created_items = await self.uow.order_item.filter(order_id=order_dto.id).create(items_data)

            tickets_to_insert = [
                {"category_id": row.category_id, "order_item_id": row.id}
                for row in created_items
                for _ in range(row.quantity)
            ]
            if tickets_to_insert:
                await self.uow.ticket.create(tickets_to_insert)

            for item in created_items:
                item.category = categories_map[item.category_id]
            order_dto.items = created_items

            await self.uow.commit()

        await self.tasks.perform_task(name="order:cancel_reservation", delay=900, order_id=order_dto.id)
        return OrderResponseSchema.model_validate(order_dto)

    async def get(self, user_id: int, obj_id: int) -> OrderResponseSchema:
        async with self.uow.as_readonly():
            obj = await (
                self.uow.order
                .with_joined("items__category")
                .get(id=obj_id)
            )
            if not obj or not obj.user_id == user_id:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

        return OrderResponseSchema.model_validate(obj)

    async def create_payment_session(
        self,
        obj_id: int,
        user_id: Optional[int],
        data: PaymentSessionCreateSchema,
    ) -> PaymentSessionResponseSchema:
        async with self.uow.as_readonly():
            order: OrderDTO = await (
                self.uow.order
                .with_joined("items__category", "user")
                .get(id=obj_id)
            )
            if not order:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

            if user_id is not None and order.user_id != user_id:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

            if order.status != OrderStatus.PENDING:
                raise WrongStateException(expected=OrderStatus.PENDING, current=order.status)

        total_amount = sum((item.purchase_price or 0.0) * item.quantity for item in order.items)
        customer_email = order.anonymous_email or (order.user.email if order.user else None)

        gateway = get_payment_gateway()
        intent = await gateway.create_payment_intent(
            order_id=order.id,
            amount=total_amount,
            currency=data.currency,
            customer_email=customer_email,
            description=f"Ticket Order #{order.id}",
            metadata={"order_id": str(order.id)},
        )

        return PaymentSessionResponseSchema(
            order_id=order.id,
            payment_intent_id=intent.id,
            amount=intent.amount,
            currency=intent.currency,
            status=intent.status,
            checkout_url=intent.checkout_url,
            client_secret=intent.client_secret,
            provider=intent.provider,
        )

    async def process_payment_webhook(self, payload: bytes, signature: Optional[str] = None) -> bool:
        gateway = get_payment_gateway()
        event_data = await gateway.verify_webhook_event(payload=payload, signature=signature)

        event_type = event_data.get("event") or event_data.get("type", "")
        data_obj = event_data.get("data", {})
        order_id = data_obj.get("order_id") or data_obj.get("metadata", {}).get("order_id")

        if order_id:
            order_id = int(order_id)
            if event_type in ("payment_intent.succeeded", "checkout.session.completed", "charge.succeeded"):
                await self.confirm_payment(obj_id=order_id)
            elif event_type in ("payment_intent.payment_failed", "charge.failed"):
                await self.expire_order(obj_id=order_id)

        return True

    async def confirm_payment(self, obj_id: int) -> bool:
        async with self.uow:
            order_res = await (
                self.uow.order
                .filter(id=obj_id, status=OrderStatus.PENDING)
                .update(status=OrderStatus.PAID, returning=False)
            )

            if not order_res:
                order_obj = await self.uow.order.get(id=obj_id)
                if not order_obj:
                    raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

                if order_obj.status == OrderStatus.PAID:
                    return True

                raise WrongStateException(expected=OrderStatus.PENDING)

            items = await self.uow.order_item.filter(order_id=obj_id).all()
            item_ids = [item.id for item in items]

            if item_ids:
                await (
                    self.uow.ticket
                    .filter(order_item_id__in=item_ids)
                    .update(status=TicketStatus.PAID, returning=False)
                )

            await self.uow.commit()

        await self.tasks.perform_task(name="order:send_confirmation_mail", order_id=obj_id)
        return True

    async def cancel_order(
        self,
        obj_id: int,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> OrderCancelResponseSchema:
        async with self.uow:
            order_obj: OrderDTO = await (
                self.uow.order
                .with_joined("items__category__event", "user")
                .get(id=obj_id)
            )

            if not order_obj:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

            if user_id is not None and not is_admin and order_obj.user_id != user_id:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

            if order_obj.status == OrderStatus.CANCELLED:
                return OrderCancelResponseSchema(
                    order_id=obj_id,
                    status=OrderStatus.CANCELLED,
                    refund_issued=False,
                    message="Order is already cancelled",
                )

            refund_issued = False
            if order_obj.status == OrderStatus.PAID:
                # Validate event has not started yet
                if order_obj.items and order_obj.items[0].category and order_obj.items[0].category.event:
                    event = order_obj.items[0].category.event
                    if event.started_at:
                        now = datetime.now(timezone.utc)
                        event_start = event.started_at
                        if event_start.tzinfo is None:
                            event_start = event_start.replace(tzinfo=timezone.utc)
                        if event_start <= now:
                            raise ServiceException("Cannot cancel order: Event has already started or concluded.")

                total_amount = sum((item.purchase_price or 0.0) * item.quantity for item in order_obj.items)
                gateway = get_payment_gateway()
                await gateway.refund_payment(order_id=obj_id, amount=total_amount)
                refund_issued = True

            # Update order status to CANCELLED
            await (
                self.uow.order
                .filter(id=obj_id)
                .update(status=OrderStatus.CANCELLED, returning=False)
            )

            # Destructively delete ticket holdings so category quotas/available quantities are immediately restored
            await self.uow.ticket.filter(order_item__order_id=obj_id).delete()
            await self.uow.commit()

        await self.tasks.perform_task(
            name="order:send_cancellation_mail",
            order_id=obj_id,
            refund_issued=refund_issued,
        )

        message = (
            "Order cancelled and refund processed successfully."
            if refund_issued
            else "Order reservation cancelled successfully."
        )

        return OrderCancelResponseSchema(
            order_id=obj_id,
            status=OrderStatus.CANCELLED,
            refund_issued=refund_issued,
            message=message,
        )

    async def expire_order(self, obj_id: int) -> bool:
        async with self.uow:
            order_res = await (
                self.uow.order
                .filter(id=obj_id, status=OrderStatus.PENDING)
                .update(status=OrderStatus.CANCELLED, returning=False)
            )

            if not order_res:
                order_obj = await self.uow.order.get(id=obj_id)
                if not order_obj:
                    raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=obj_id)

                if order_obj.status == OrderStatus.CANCELLED:
                    return True

                return False

            await self.uow.ticket.filter(order_item__order_id=obj_id).delete()
            await self.uow.commit()

        return True

    async def migrate_anonymous_orders(self, email: str) -> int:
        async with self.uow:
            user_obj = await self.uow.user.get(email=email)
            if not user_obj:
                raise ObjectNotFoundException(table=self.uow.user.get_model_name(), value=email)

            migrated_count = await (
                self.uow.order
                .filter(anonymous_email=email)
                .update(user_id=user_obj.id, anonymous_email=None, returning=False)
            )

            if migrated_count > 0:
                await self.uow.commit()

        return migrated_count

    async def get_email_notification_data(
        self,
        order_id: int,
        refund_issued: bool = False,
    ) -> OrderEmailDataSchema:
        async with self.uow.as_readonly():
            obj: OrderDTO = await (
                self.uow.order
                .with_joined(
                    "items__category__event",
                    "user"
                )
                .get(id=order_id)
            )

            if not obj:
                raise ObjectNotFoundException(table=self.uow.order.get_model_name(), value=order_id)

        target_email = obj.anonymous_email or (obj.user.email if obj.user else "")
        event_title = "Event"
        event_started_at = None
        event_address = None

        if obj.items and obj.items[0].category and obj.items[0].category.event:
            event_obj: EventDTO = obj.items[0].category.event
            event_title = event_obj.title
            event_started_at = event_obj.started_at
            event_address = event_obj.address

        email_items = []
        for item in (obj.items or []):
            cat_name = item.category.name if item.category else f"Category #{item.category_id}"
            price = item.purchase_price if item.purchase_price is not None else (item.category.price if item.category else 0.0)
            email_items.append(
                OrderEmailItemSchema(
                    category_name=cat_name,
                    price_paid=price,
                    quantity=item.quantity,
                )
            )

        data = {
            "order_id": obj.id,
            "created_at": obj.created_at,
            "user_email": target_email,
            "event_title": event_title,
            "event_started_at": event_started_at,
            "event_address": event_address,
            "items": email_items,
            "refund_issued": refund_issued,
        }

        return OrderEmailDataSchema.model_validate(data)

    async def get_all_by_user_id(
            self,
            user_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[OrderResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.order
                .filter(user_id=user_id, **(filters or {}))
                .with_joined("items__category")
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=OrderResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )

    async def get_all_items_by_user_id(
            self,
            user_id: int,
            *,
            filters: dict[str, Any] | None = None,
            offset: int = 0,
            limit: int = 100,
            order_by: str | None = None,
    ) -> PaginatedResponseSchema[OrderItemResponseSchema]:
        async with self.uow.as_readonly():
            items, count = await (
                self.uow.order_item
                .filter(order__user_id=user_id, **(filters or {}))
                .with_joined("category")
                .order_by(order_by)
                .paginate(offset=offset, limit=limit)
            )

        return self._paginate(
            schema=OrderItemResponseSchema,
            items=items,
            total_items=count,
            limit=limit,
        )
