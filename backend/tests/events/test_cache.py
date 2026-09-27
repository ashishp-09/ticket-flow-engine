from starlette import status

from core.types import AsUserClient, EventContext
from src.modules.event.models import EventState


class TestEventsCache:
    async def test_endpoint_cache_hit(self, as_verified_user: AsUserClient, event_context: EventContext, create_event):
        cat, usr = await event_context()
        await create_event(user_id=usr.id, category_id=cat.id)

        client = as_verified_user(user_id=usr.id)

        first_response = await client.get("/events")
        assert first_response.status_code == status.HTTP_200_OK

        await create_event(user_id=usr.id, category_id=cat.id)

        second_response = await client.get("/events")
        assert second_response.status_code == status.HTTP_200_OK

        assert first_response.json()["count"] == second_response.json()["count"]

    async def test_endpoint_cache_invalidation(self, as_verified_user: AsUserClient, as_moderator,
                                               event_context: EventContext, create_event):
        cat, usr = await event_context()

        client = as_verified_user()
        first_response = await client.get("/events")
        assert first_response.status_code == status.HTTP_200_OK

        event = await create_event(user_id=usr.id, category_id=cat.id, state=EventState.ON_MODERATION)
        moderator_client = as_moderator()
        response = await moderator_client.patch(f"/moderation/events/{event.id}", json={"result": True})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        second_response = await client.get("/events")
        assert second_response.status_code == status.HTTP_200_OK

        assert first_response.json()["count"] != second_response.json()["count"]
