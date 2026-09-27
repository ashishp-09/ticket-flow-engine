from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from src.modules.event.models import EventState


class TestUserEventsManagement:
    user_role = "verified_user"

    async def test_create_event_success(self, api_client, setup_uow, seed_event_environment):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await uow.commit()

        payload = {
            "category_id": 1,
            "title": "Concert",
            "description": "Rock music event",
            "format": "online",
            "started_at": (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0).isoformat(),
        }
        response = await api_client.post("/events", json=payload)
        assert response.status_code == status.HTTP_201_CREATED

    async def test_create_event_invalid_data(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd")
            await uow.commit()

        payload = {
            "category_id": 1,
            "title": "",
            "description": "Rock music event",
            "format": "online",
            "started_at": "2026-06-20T18:00:00+00:00",
        }
        response = await api_client.post("/events", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_update_event_success(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Non Draft",
                description="Desc",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        payload = {"title": "New Title"}
        response = await api_client.patch("/events/1", json=payload)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = await api_client.get("/events/my/1")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "New Title"

    async def test_update_event_non_draft_fails(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Non Draft",
                description="Desc",
                state="approved",
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        payload = {"title": "New Title"}
        response = await api_client.patch("/events/1", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_get_my_events_success(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="My Event",
                description="Desc",
                state=EventState.DRAFT,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events/my?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "results" in data

        assert data.get("count") == 1
        assert len(data["results"]) == 1

        assert data["results"][0]["title"] == "My Event"

    async def test_get_event_private_success(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="My Event",
                description="Desc",
                state=EventState.DRAFT,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events/my/1")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "My Event"

    async def test_get_event_private_nonexistent(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        response = await api_client.get("/events/1")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPublicEventsCatalog:
    async def test_get_event_public_success(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="My Event",
                description="Desc",
                state=EventState.APPROVED,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events/1")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["title"] == "My Event"

    async def test_get_event_public_wrong_state(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        async with setup_uow as uow:
            await seed_event_environment(uow)
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="My Event",
                description="Desc",
                state=EventState.DRAFT,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events/1")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_event_public_nonexistent(self, api_client, setup_uow, seed_event_environment, create_model_factory):
        response = await api_client.get("/events/1")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_create_event_unauthorized(self, api_client):
        payload = {
            "category_id": 1,
            "title": "Concert",
            "description": "Rock music event",
            "format": "online",
            "started_at": "2026-06-20T18:00:00+00:00",
        }
        response = await api_client.post("/events", json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_categories_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await uow.commit()

        response = await api_client.get("/events/categories?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "results" in data

        assert isinstance(data.get("results"), list)
        assert len(data["results"]) == 1

        assert data["results"][0]["name"] == "Music"

    async def test_get_upcoming_events_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Future Concert",
                description="Future Desc",
                state=EventState.APPROVED,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events?limit=10&offset=0")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "results" in data
        assert isinstance(data.get("results"), list)

        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "Future Concert"

    @pytest.mark.parametrize("hidden_state", [EventState.DRAFT, EventState.CANCELLED])
    async def test_get_upcoming_events_excludes_hidden_states(self, api_client, setup_uow, create_model_factory,
                                                              hidden_state):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Hidden Event",
                description="Desc",
                state=hidden_state,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/events")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data.get("items", [])) == 0
