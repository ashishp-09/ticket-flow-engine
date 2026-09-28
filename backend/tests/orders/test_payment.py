import asyncio
import uuid

import pytest
from fastapi import status

from src.modules.order.models import OrderStatus


class TestOrderPayment:
    user_role = "user"

    async def test_pay_order_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=777, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=777).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        response = await api_client.patch("/orders/777/pay")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = await api_client.get("/orders/777")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == OrderStatus.PAID

    async def test_pay_order_idempotency_cache_hit(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=888, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=888).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        idempotency_key = str(uuid.uuid4())
        headers = {"Idempotency-Key": idempotency_key}

        first_response = await api_client.patch("/orders/888/pay", headers=headers)
        assert first_response.status_code == status.HTTP_204_NO_CONTENT

        second_response = await api_client.patch("/orders/888/pay", headers=headers)
        assert second_response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("invalid_status", [OrderStatus.CANCELLED])
    async def test_pay_order_invalid_status_fails(self, api_client, setup_uow, seed_order_env, create_model_factory,
                                                  invalid_status):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=444, status=invalid_status, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=444).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        response = await api_client.patch("/orders/444/pay")
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_pay_non_existent_order(self, api_client, setup_uow, seed_order_env):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await uow.commit()

        response = await api_client.patch("/orders/2147483646/pay")
        assert response.status_code == status.HTTP_404_NOT_FOUND
