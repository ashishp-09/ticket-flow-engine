from fastapi import status

from src.modules.order.models import OrderStatus
from src.modules.ticket.models import TicketStatus


class TestUserTicketsCatalog:
    user_role = "verified_user"

    async def test_get_my_tickets_success(self, api_client, setup_uow, seed_order_env, create_model_factory):
        async with setup_uow as uow:
            await seed_order_env(uow)

            order = await create_model_factory(
                uow,
                "order",
                id=10,
                status=OrderStatus.PAID,
                user_id=1,
                anonymous_email=None
            )

            order_item = await create_model_factory(
                uow,
                "order_item",
                id=20,
                order_id=order.id,
                category_id=1,
                quantity=1,
                purchase_price=100.0
            )

            await create_model_factory(
                uow,
                "ticket",
                id=1,
                category_id=1,
                order_item_id=order_item.id,
                status=TicketStatus.PAID
            )
            await uow.commit()

        response = await api_client.get("/tickets/my?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 1
