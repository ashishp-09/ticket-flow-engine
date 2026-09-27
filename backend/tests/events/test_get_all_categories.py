import pytest

from core.constants import EVENT_CATEGORIES_PATH
from core.mixins.filter_validation_errors import FilterValidationErrorsMixin
from core.mixins.pagination_errors import OrderByErrorsMixin, PaginationErrorsMixin
from core.testing.base import APITestBase
from core.types import AsAnonymClient, EventCategoryFactory, EventContext, EventFactory


class TestGetCategories(
    FilterValidationErrorsMixin.with_params(
        path=EVENT_CATEGORIES_PATH,
        filters={
            "name__icontains": (str, {"max_length": 100}),
            "parent_id": (int, {"min_value": 1}),
        }
    ),
    PaginationErrorsMixin.with_params(EVENT_CATEGORIES_PATH),
    OrderByErrorsMixin.with_params(EVENT_CATEGORIES_PATH, invalid_field="parent_id"),
    APITestBase,
):

    async def test_filters_by_parent_id(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory,
    ) -> None:
        parent_cat = await create_event_category()
        child_cat = await create_event_category(parent_id=parent_cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            query_params={"parent_id": parent_cat.id}
        )

        assert item.get("id") == child_cat.id
        assert item.get("name") == child_cat.name

    async def test_strips_whitespace_from_name(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        cat = await create_event_category()

        item = await self._get_first_and_only_of_paginated(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            query_params={"name__icontains": " Event "}
        )

        assert item.get("id") == cat.id
        assert item.get("name") == cat.name

    async def test_filters_root_categories_only(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory,
    ) -> None:
        parent_cat = await create_event_category()
        await create_event_category(parent_id=parent_cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            query_params={"parent_id__is_null": True}
        )

        assert item.get("id") == parent_cat.id
        assert item.get("name") == parent_cat.name

    async def test_filters_by_can_create_events(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory,
    ):
        parent_cat = await create_event_category()
        child_cat = await create_event_category(parent_id=parent_cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            query_params={"can_create_events": True}
        )

        assert item.get("id") == child_cat.id
        assert item.get("name") == child_cat.name

    async def test_filters_by_can_create_subcategories(
            self,
            as_anonym: AsAnonymClient,
            event_context: EventContext,
            create_event_category: EventCategoryFactory,
            create_event: EventFactory,
    ) -> None:
        cat, usr = await event_context()
        events_cat = await create_event_category()
        await create_event(user_id=usr.id, category_id=events_cat.id)

        item = await self._get_first_and_only_of_paginated(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            query_params={"can_create_subcategories": True}
        )

        assert item.get("id") == cat.id
        assert item.get("name") == cat.name

    @pytest.mark.parametrize("value", ["id", "name", "-id", "-name"])
    async def test_orders_by_field(
            self,
            value: str,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        earlier = await create_event_category(name="A-Event Category")
        later = await create_event_category(name="B-Event Category")

        await self._assert_sorting_success(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            sorting_field=value,
            earlier_obj=earlier,
            later_obj=later,
        )

    @pytest.mark.parametrize("value", [1, 2])
    async def test_applies_limit(
            self,
            value: int,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        for _ in range(value + 1):
            await create_event_category()

        await self._assert_limit_applied(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            limit=value
        )

    async def test_applies_offset(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        await create_event_category()
        cat = await create_event_category()

        await self._assert_offset_applied(
            client=as_anonym(),
            path=EVENT_CATEGORIES_PATH,
            offset=1,
            lookup_value=cat.id
        )

    async def test_returns_all_categories_for_main_page(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        cat = await create_event_category()
        await create_event_category(parent_id=cat.id)

        resp = await as_anonym().get(EVENT_CATEGORIES_PATH)

        assert self._count_of_paginated_response(resp) == 2

        assert self._first_of_paginated_response(resp)["name"] == cat.name

    async def test_returns_empty_list_when_no_matches_found(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        await create_event_category()

        resp = await as_anonym().get(EVENT_CATEGORIES_PATH, params={"name__icontains": "Title"})

        assert self._count_of_paginated_response(resp) == 0

    async def test_cache_hit(
            self,
            as_anonym: AsAnonymClient,
            create_event_category: EventCategoryFactory
    ) -> None:
        cat = await create_event_category()
        client = as_anonym()

        # First request primes cache
        resp1 = await client.get(EVENT_CATEGORIES_PATH)
        assert resp1.status_code == 200

        # Second request hits cache
        resp2 = await client.get(EVENT_CATEGORIES_PATH)
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()
