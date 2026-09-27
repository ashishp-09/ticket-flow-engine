from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from src.modules.event.models import EventState
from src.modules.ticket.models import TicketStatus


class TestUserEvents:
    user_role = "verified_user"

    @pytest.mark.parametrize("action, initial_state", [("publish", EventState.DRAFT), ("cancel", EventState.DRAFT)])
    async def test_event_action_success(
            self, api_client, setup_uow, seed_event_environment, create_model_factory, action, initial_state
    ):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Event",
                description="Desc",
                state=initial_state,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.patch(f"/events/1/{action}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize("action", ["cancel", "publish"])
    async def test_event_action_not_found(self, api_client, setup_uow, create_model_factory, action):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd")
            await uow.commit()

        response = await api_client.patch(f"/events/2147483646/{action}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "action, initial_state",
        [("publish", EventState.DRAFT), ("cancel", EventState.APPROVED), ("update", EventState.DRAFT)],
    )
    async def test_event_action_forbidden_for_stranger(self, api_client, setup_uow, create_model_factory, action,
                                                       initial_state):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd")
            await create_model_factory(uow, "user", id=2, email="test2@test.com", username="user2", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=2,
                title="Stranger Event",
                description="Desc",
                state=initial_state,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        if action == "update":
            response = await api_client.patch("/events/1", json={"title": "Hack Title"})
        else:
            response = await api_client.patch(f"/events/1/{action}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_publish_event_idempotency(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Already Published",
                description="Desc",
                state=EventState.ON_MODERATION,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.patch("/events/1/publish")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_cancel_event_idempotency(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Already Cancelled",
                description="Desc",
                state="cancelled",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.patch("/events/1/cancel")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.parametrize(
        "url",
        [
            "/events/categories?limit=0",
        ],
    )
    async def test_get_events_invalid_pagination_params_protected(self, api_client, url):
        response = await api_client.get(url)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.parametrize("limit, expected_count", [("10", 2), ("1", 1)])
    async def test_get_all_tickets_for_event_success_and_pagination(
            self, api_client, setup_uow, seed_event_environment, create_model_factory, limit, expected_count
    ):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Concert",
                description="Rock",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await create_model_factory(
                uow, "ticket_category", id=1, event_id=1, name="Standard", price=100.0, total_quantity=100
            )
            await create_model_factory(
                uow, "ticket", id=101, category_id=1, order_item_id=None, status=TicketStatus.RESERVED
            )
            await create_model_factory(
                uow, "ticket", id=102, category_id=1, order_item_id=None, status=TicketStatus.RESERVED
            )
            await uow.commit()

        response = await api_client.get(f"/events/1/tickets?limit={limit}&offset=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == expected_count

    async def test_get_all_tickets_for_event_empty_list(self, api_client, setup_uow, seed_event_environment,
                                                        create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Concert",
                description="Rock",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events/1/tickets?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 0


class TestPublicEvents:
    @pytest.mark.parametrize(
        "url",
        [
            "/events?limit=-5",
            "/events?offset=abc",
        ],
    )
    async def test_get_events_invalid_pagination_params_public(self, api_client, url):
        response = await api_client.get(url)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_get_all_tickets_for_event_forbidden(self, api_client, get_auth_headers, setup_uow,
                                                       create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="owner@test.com", username="owner", password="pwd")
            await create_model_factory(uow, "user", id=2, email="stranger@test.com", username="stranger",
                                       password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Concert",
                description="Rock",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        headers = get_auth_headers(user_id=2, role="verified_user")
        response = await api_client.get("/events/1/tickets?limit=10&offset=0", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_all_tickets_for_event_unauthorized(self, api_client):
        response = await api_client.get("/events/1/tickets?limit=10&offset=0")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
