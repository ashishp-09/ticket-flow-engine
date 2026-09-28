import pytest
from fastapi import status

from src.modules.order.models import OrderStatus
from src.modules.ticket.models import TicketStatus


class TestOrderCancellation:
    user_role = "user"

    async def test_cancel_pending_order_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=555, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=555).create(category_id=1, quantity=1, purchase_price=100.0)
            await uow.ticket.create(category_id=1, order_item_id=item.id, status=TicketStatus.RESERVED)
            await uow.commit()

        response = await api_client.post("/orders/555/cancel")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["order_id"] == 555
        assert data["status"] == OrderStatus.CANCELLED
        assert data["refund_issued"] is False

        # Verify tickets are deleted and freed
        async with setup_uow as uow:
            tickets = await uow.ticket.filter(order_item__order_id=555).all()
            assert len(tickets) == 0

    async def test_cancel_paid_order_issues_refund(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=666, status=OrderStatus.PAID, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=666).create(category_id=1, quantity=1, purchase_price=100.0)
            await uow.ticket.create(category_id=1, order_item_id=item.id, status=TicketStatus.PAID)
            await uow.commit()

        response = await api_client.post("/orders/666/cancel")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["order_id"] == 666
        assert data["status"] == OrderStatus.CANCELLED
        assert data["refund_issued"] is True

    async def test_cancel_already_cancelled_order_is_idempotent(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=999, status=OrderStatus.CANCELLED, user_id=1, anonymous_email=None
            )
            await uow.commit()

        response = await api_client.post("/orders/999/cancel")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["order_id"] == 999
        assert data["status"] == OrderStatus.CANCELLED

    async def test_cancel_non_existent_order(self, api_client, setup_uow, seed_order_env):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await uow.commit()

        response = await api_client.post("/orders/999999/cancel")
        assert response.status_code == status.HTTP_404_NOT_FOUND
