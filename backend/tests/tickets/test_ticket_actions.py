import pytest
from fastapi import status

from src.modules.order.models import OrderStatus
from src.modules.ticket.models import TicketStatus
from src.modules.user.models import UserRole


class TestTicketActions:
    user_role = "user"

    async def test_get_ticket_by_id(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=101, status=OrderStatus.PAID, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=101).create(category_id=1, quantity=1, purchase_price=75.0)
            ticket = await uow.ticket.create(id=501, category_id=1, order_item_id=item.id, status=TicketStatus.PAID)
            await uow.commit()

        response = await api_client.get("/tickets/501")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 501
        assert data["status"] == TicketStatus.PAID
        assert data["category_id"] == 1

    async def test_check_in_ticket(self, api_client, setup_uow, seed_order_env, create_model_factory):
        # User 1 is the event organizer (from seed_order_env)
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=102, status=OrderStatus.PAID, user_id=2, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=102).create(category_id=1, quantity=1, purchase_price=75.0)
            await uow.ticket.create(id=502, category_id=1, order_item_id=item.id, status=TicketStatus.PAID)
            await uow.commit()

        response = await api_client.post("/tickets/502/check-in")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticket_id"] == 502
        assert data["status"] == TicketStatus.CHECKED_IN

        # Second check-in attempt should fail
        response = await api_client.post("/tickets/502/check-in")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_transfer_ticket(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            # Create recipient user
            await create_model_factory(
                uow, "user", id=3, email="recipient@example.com", username="recipient", password="password", role=UserRole.USER, is_active=True
            )
            await create_model_factory(
                uow, "order", id=103, status=OrderStatus.PAID, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=103).create(category_id=1, quantity=1, purchase_price=75.0)
            await uow.ticket.create(id=503, category_id=1, order_item_id=item.id, status=TicketStatus.PAID)
            await uow.commit()

        body = {"target_email": "recipient@example.com"}
        response = await api_client.post("/tickets/503/transfer", json=body)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticket_id"] == 503
        assert data["target_email"] == "recipient@example.com"
