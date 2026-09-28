from datetime import datetime, timezone, timedelta

import pytest

from src.modules.event.models import EventState, EventFormat


@pytest.fixture
def user_headers(get_auth_headers):
    return get_auth_headers(user_id=1, role="verified_user")


@pytest.fixture
def user_client(client, user_headers):
    client.headers.update(user_headers)
    return client


@pytest.fixture
def seed_order_env(create_model_factory):
    async def _seed(uow, state=EventState.APPROVED):
        user = await create_model_factory(uow, "user", id=1, email="test@test.com", username="user", password="pwd")
        event_cat = await create_model_factory(uow, "event_category", id=1, name="Music")

        event = await create_model_factory(
            uow,
            "event",
            id=1,
            user_id=user.id,
            state=state,
            title="Test Event",
            description="Desc",
            category_id=event_cat.id,
            format=EventFormat.ONLINE,
            started_at=datetime.now(timezone.utc) + timedelta(days=10),
        )

        await create_model_factory(
            uow,
            "ticket_category",
            id=1,
            event_id=event.id,
            name="Standard",
            price=100,
            total_quantity=100
        )

    return _seed
