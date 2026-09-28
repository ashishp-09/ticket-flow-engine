import pytest
from fastapi import status

from src.modules.order.models import OrderStatus


class TestUserOrdersManagement:
    user_role = "verified_user"

    async def test_create_order_authorized_success(self, api_client, setup_uow, seed_order_env):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await uow.commit()

        response = await api_client.post("/orders", json={"items": [{"category_id": 1, "quantity": 2}]})
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == OrderStatus.PENDING
        assert data["user_id"] == 1

        async with setup_uow as uow:
            category = await uow.ticket_category.filter(id=1).with_joined("items").first()
            assert category.occupied_count == 2

    async def test_get_order_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=123, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=123).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        response = await api_client.get("/orders/123")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == 123

    async def test_get_my_orders_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=1, status=OrderStatus.PENDING, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=1).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        response = await api_client.get("/orders")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    async def test_get_my_items_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await create_model_factory(
                uow, "order", id=2, status=OrderStatus.PAID, user_id=1, anonymous_email=None
            )
            item = await uow.order_item.filter(order_id=2).create(category_id=1, quantity=1)
            await uow.ticket.create(category_id=1, order_item_id=item.id)
            await uow.commit()

        response = await api_client.get("/orders/items")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1

    @pytest.mark.parametrize("invalid_quantity", [0, -1, -5])
    async def test_create_order_invalid_quantity(self, api_client, setup_uow, seed_order_env, invalid_quantity):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await uow.commit()

        response = await api_client.post("/orders", json={"items": [{"category_id": 1, "quantity": invalid_quantity}]})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestAnonymousAndPublicOrders:
    async def test_create_order_anonymous_success(self, api_client, setup_uow, seed_order_env):
        async with setup_uow as uow:
            await seed_order_env(uow)
            await uow.commit()

        payload = {"items": [{"category_id": 1, "quantity": 1}], "anonymous_email": "anon@test.com"}
        response = await api_client.post("/orders", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == OrderStatus.PENDING
        assert data["user_id"] is None
        assert data["anonymous_email"] == "anon@test.com"

    async def test_create_order_insufficient_quota(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)
            order = await create_model_factory(uow, "order", anonymous_email="old@test.com")
            item = await uow.order_item.filter(order_id=order.id).create(category_id=1, quantity=100)
            await uow.ticket.create([
                {"category_id": 1, "order_item_id": item.id}
                for _ in range(100)
            ])
            await uow.commit()

        payload = {"items": [{"category_id": 1, "quantity": 1}], "anonymous_email": "buyer@test.com"}
        response = await api_client.post("/orders", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT
