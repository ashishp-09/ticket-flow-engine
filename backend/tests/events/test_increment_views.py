import asyncio

from faststream.kafka import TestKafkaBroker

from core.constants import EVENT_DETAILS_PATH, EVENTS_INCREMENT_VIEWS_PATH
from core.mixins.filter_validation_errors import FilterValidationErrorsMixin
from core.testing.base import APITestBase
from core.types import AsAnonymClient, EventFactory, PrivateEventContext
from src.workers.view_logs import handle_view_logs


class TestIncrementView(
    FilterValidationErrorsMixin.with_params(
        path=EVENTS_INCREMENT_VIEWS_PATH,
        filters={
            "object_ids": list,
        }
    ),
    APITestBase,
):
    async def test_increments_view_for_one(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        _, _, event = await private_event_context()

        await self._assert_accepted(
            client=as_anonym(),
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        item = await self._get_item_by_id(
            client=as_anonym(),
            path=EVENT_DETAILS_PATH,
            obj_id=event.id,
        )

        assert item["views"] == 1

    async def test_increments_view_for_multiple(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        cat, usr, first_event = await private_event_context()
        second_event = await create_event(category_id=cat.id, user_id=usr.id)

        await self._assert_accepted(
            client=as_anonym(),
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [first_event.id, second_event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        for event in [first_event, second_event]:
            item = await self._get_item_by_id(
                client=as_anonym(),
                path=EVENT_DETAILS_PATH,
                obj_id=event.id,
            )

            assert item["views"] == 1

    async def test_view_idempotency(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        _, _, event = await private_event_context()
        client = as_anonym()

        await self._assert_accepted(
            client=client,
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        await self._assert_accepted(
            client=client,
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id]},
        )

        item = await self._get_item_by_id(
            client=client,
            path=EVENT_DETAILS_PATH,
            obj_id=event.id,
        )

        assert item["views"] == 1

    async def test_partially_unique_batch_filtering(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            create_event: EventFactory,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        cat, usr, first_event = await private_event_context()
        second_event = await create_event(category_id=cat.id, user_id=usr.id)
        client = as_anonym()

        await self._assert_accepted(
            client=client,
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [first_event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        await self._assert_accepted(
            client=client,
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [first_event.id, second_event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        for event in [first_event, second_event]:
            item = await self._get_item_by_id(
                client=as_anonym(),
                path=EVENT_DETAILS_PATH,
                obj_id=event.id,
            )

            assert item["views"] == 1

    async def test_views_increment_for_different_visitors(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        _, _, event = await private_event_context()

        await self._assert_accepted(
            client=as_anonym(),
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id]},
        )

        await self._assert_accepted(
            client=as_anonym(),
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        item = await self._get_item_by_id(
            client=as_anonym(),
            path=EVENT_DETAILS_PATH,
            obj_id=event.id,
        )

        assert item["views"] == 2

    async def test_duplicate_object_ids_in_single_batch_collapsed(
            self,
            as_anonym: AsAnonymClient,
            private_event_context: PrivateEventContext,
            mock_kafka: TestKafkaBroker,
    ) -> None:
        _, _, event = await private_event_context()

        await self._assert_accepted(
            client=as_anonym(),
            method="POST",
            path=EVENTS_INCREMENT_VIEWS_PATH,
            data={"object_ids": [event.id, event.id]},
        )

        await handle_view_logs.wait_call(timeout=3.0)

        item = await self._get_item_by_id(
            client=as_anonym(),
            path=EVENT_DETAILS_PATH,
            obj_id=event.id,
        )

        assert item["views"] == 1
