from datetime import datetime, timedelta, timezone

import pytest

from core.constants import PRIVATE_EVENTS_PATH
from core.mixins.access_errors import UnauthenticatedAccessMixin, UnauthorizedAccessMixin
from core.mixins.filter_validation_errors import FilterValidationErrorsMixin
from core.mixins.pagination_errors import OrderByErrorsMixin, PaginationErrorsMixin
from core.testing.base import APITestBase
from core.types import AsUserClient, EventCategoryFactory, EventContext, EventFactory, PrivateEventContext, UserFactory
from src.modules.event.models import EventFormat
from src.modules.user.models import UserRole


class TestGetAllPrivate(
    FilterValidationErrorsMixin.with_params(
        path=PRIVATE_EVENTS_PATH,
        role=UserRole.VERIFIED_USER,
        filters={
            "category_id": (int, {"min_value": 1}),
            "title__icontains": (str, {"max_length": 100}),
            "address": (str, {"max_length": 256}),
            "format": (str, {"extra_values": ["OFFLINE", "ONLINE"]}),
            "started_at": datetime,
            "started_at__gte": datetime,
            "started_at__lte": datetime,
        }
    ),
    PaginationErrorsMixin.with_params(PRIVATE_EVENTS_PATH, UserRole.VERIFIED_USER),
    OrderByErrorsMixin.with_params(PRIVATE_EVENTS_PATH, UserRole.VERIFIED_USER, invalid_field="address"),
    UnauthenticatedAccessMixin.with_params("GET", PRIVATE_EVENTS_PATH),
    UnauthorizedAccessMixin.with_params("GET", PRIVATE_EVENTS_PATH, UserRole.USER),
    APITestBase,
):
    async def test_filters_by_category_id(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
            create_event_category: EventCategoryFactory,
    ) -> None:
        cat, usr, event = await private_event_context()

        noise_cat = await create_event_category()
        await create_event(user_id=usr.id, category_id=noise_cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"category_id": cat.id},
        )

        assert item.get("id") == event.id
        assert item.get("title") == event.title

    async def test_filters_by_title(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, event = await private_event_context(event_title="Event Title")
        await create_event(user_id=usr.id, category_id=cat.id, title="Noise Title")

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"title__icontains": event.title},
        )

        assert item.get("id") == event.id
        assert item.get("title") == event.title

    @pytest.mark.parametrize("value", [EventFormat.OFFLINE, EventFormat.ONLINE])
    async def test_filters_by_format(
            self,
            value: str,
            as_verified_user: AsUserClient,
            event_context: EventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr = await event_context(user_role=UserRole.VERIFIED_USER)
        offline_event = await create_event(user_id=usr.id, category_id=cat.id, format=EventFormat.OFFLINE)
        online_event = await create_event(user_id=usr.id, category_id=cat.id)

        target_event = offline_event if value == EventFormat.OFFLINE else online_event

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"format": target_event.format},
        )

        assert item.get("id") == target_event.id
        assert item.get("format") == target_event.format

    async def test_filters_by_address(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, event = await private_event_context(event_format=EventFormat.OFFLINE, event_address="Event Address")
        await create_event(user_id=usr.id, category_id=cat.id, format=EventFormat.OFFLINE)

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"address": event.address},
        )

        assert item.get("id") == event.id
        assert item.get("address") == event.address

    async def test_filters_by_started_at(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, event = await private_event_context()
        await create_event(user_id=usr.id, category_id=cat.id, started_at=event.started_at + timedelta(seconds=1))

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"started_at": event.started_at},
        )

        assert item.get("id") == event.id
        api_started_at = datetime.fromisoformat(item.get("started_at"))
        assert api_started_at == event.started_at

    async def test_filters_by_started_at__gte(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, event = await private_event_context()
        await create_event(
            user_id=usr.id,
            category_id=cat.id,
            started_at=event.started_at - timedelta(days=1)
        )

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"started_at__gte": event.started_at - timedelta(seconds=1)},
        )

        assert item.get("id") == event.id
        api_started_at = datetime.fromisoformat(item.get("started_at"))
        assert api_started_at == event.started_at

    async def test_filters_by_started_at__lte(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, event = await private_event_context()
        await create_event(
            user_id=usr.id,
            category_id=cat.id,
            started_at=event.started_at + timedelta(days=1)
        )

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            query_params={"started_at__lte": event.started_at + timedelta(seconds=1)},
        )

        assert item.get("id") == event.id
        api_started_at = datetime.fromisoformat(item.get("started_at"))
        assert api_started_at == event.started_at

    @pytest.mark.parametrize("value", ["id", "title", "started_at", "-id", "-title", "-started_at"])
    async def test_orders_by_field(
            self,
            value: str,
            as_verified_user: AsUserClient,
            event_context: EventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr = await event_context(user_role=UserRole.VERIFIED_USER)
        base_time = datetime.now(timezone.utc)

        earlier = await create_event(
            user_id=usr.id, category_id=cat.id, title="A-First event", started_at=base_time
        )
        later = await create_event(
            user_id=usr.id, category_id=cat.id, title="B-Second event", started_at=base_time + timedelta(days=2)
        )

        await self._assert_sorting_success(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            sorting_field=value,
            earlier_obj=earlier,
            later_obj=later,
        )

    @pytest.mark.parametrize("value", [1, 2])
    async def test_applies_limit(
            self,
            value: int,
            as_verified_user: AsUserClient,
            event_context: EventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr = await event_context(user_role=UserRole.VERIFIED_USER)

        for _ in range(value + 1):
            await create_event(user_id=usr.id, category_id=cat.id)

        await self._assert_limit_applied(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            limit=value
        )

    async def test_applies_offset(
            self,
            as_verified_user: AsUserClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
    ) -> None:
        cat, usr, _ = await private_event_context()
        event = await create_event(user_id=usr.id, category_id=cat.id)

        await self._assert_offset_applied(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
            offset=1,
            lookup_value=event.id
        )

    async def test_returns_all_events_for_user(
            self,
            as_verified_user: AsUserClient,
            event_context: EventContext,
            create_event: EventFactory,
            create_user: UserFactory
    ) -> None:
        cat, usr = await event_context(user_role=UserRole.VERIFIED_USER)

        noise_user = await create_user(role=UserRole.VERIFIED_USER)
        await create_event(user_id=noise_user.id, category_id=cat.id)

        event = await create_event(user_id=usr.id, category_id=cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_verified_user(user_id=usr.id),
            path=PRIVATE_EVENTS_PATH,
        )

        assert item.get("id") == event.id

    async def test_returns_empty_list_when_user_has_no_events(
            self,
            as_verified_user: AsUserClient,
            event_context: EventContext,
            create_user: UserFactory,
            create_event: EventFactory,
    ) -> None:
        cat, usr = await event_context(user_role=UserRole.VERIFIED_USER)

        noise_user = await create_user(role=UserRole.VERIFIED_USER)
        await create_event(user_id=noise_user.id, category_id=cat.id)

        resp = await as_verified_user(user_id=usr.id).get(url=PRIVATE_EVENTS_PATH)

        assert self._count_of_paginated_response(resp) == 0
