import json
import pytest
from fastapi import status

from src.modules.order.models import OrderStatus
from src.modules.ticket.models import TicketStatus


class TestPaymentCheckout:
    user_role = "user"

    async def test_create_checkout_session(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=123, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=123).create(category_id=1, quantity=2, purchase_price=50.0)
            await uow.ticket.create(category_id=1, order_item_id=item.id, status=TicketStatus.RESERVED)
            await uow.commit()

        body = {
            "currency": "USD",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }
        response = await api_client.post("/orders/123/checkout", json=body)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["order_id"] == 123
        assert data["amount"] == 100.0
        assert data["currency"] == "USD"
        assert "payment_intent_id" in data
        assert "checkout_url" in data

    async def test_payment_webhook_succeeded(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=456, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=456).create(category_id=1, quantity=1, purchase_price=50.0)
            await uow.ticket.create(category_id=1, order_item_id=item.id, status=TicketStatus.RESERVED)
            await uow.commit()

        webhook_payload = {
            "event": "payment_intent.succeeded",
            "data": {
                "order_id": 456,
                "status": "paid",
            }
        }
        response = await api_client.post(
            "/orders/payment-webhook",
            content=json.dumps(webhook_payload),
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify order is now PAID
        response = await api_client.get("/orders/456")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == OrderStatus.PAID
