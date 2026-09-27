from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from src.modules.event.models import EventState


class TestModeratorEvents:
    user_role = "moderator"

    async def test_get_events_for_moderation_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="author@test.com", username="author", password="pwd")
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Pending Event",
                description="Pending Desc",
                state=EventState.ON_MODERATION,
                category_id=1,
                format="online",
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.get("/moderation/events?limit=10&offset=0")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"][0]["title"] == "Pending Event"

    @pytest.mark.parametrize("result", [True, False])
    async def test_moderate_event_success(self, api_client, setup_uow, create_model_factory, result):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="author@test.com", username="author", password="pwd")
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Pending Event",
                description="Pending Desc",
                category_id=1,
                format="online",
                state=EventState.ON_MODERATION,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.patch("/moderation/events/1", json={"result": result})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = await api_client.get("/events/1")
        if result:
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["title"] == "Pending Event"
        else:
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_moderate_event_not_found(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await uow.commit()

        response = await api_client.patch("/moderation/events/2147483646", json={"result": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("already_moderated_state", ["approved", "rejected"])
    async def test_moderate_event_idempotency(self, api_client, setup_uow, create_model_factory,
                                              already_moderated_state):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="author@test.com", username="author", password="pwd")
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(uow, "event_category", id=1, name="Music")
            await create_model_factory(
                uow,
                "event",
                id=1,
                user_id=1,
                title="Moderated Event",
                description="Desc",
                category_id=1,
                format="online",
                state=already_moderated_state,
                started_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            await uow.commit()

        response = await api_client.patch("/moderation/events/1", json={
            "result": True if already_moderated_state == "approved" else False})
        assert response.status_code == status.HTTP_204_NO_CONTENT
