import pytest

from core.types import EventCategoryFactory, EventContext, EventFactory, PrivateEventContext, UserFactory
from src.app.uow import create_app_uow
from src.modules.event.data_objects import EventCategoryDTO, EventDTO
from src.modules.event.models import EventFormat, EventState
from src.modules.user.data_objects import UserDTO
from src.modules.user.models import UserRole


@pytest.fixture
def user_headers(get_auth_headers):
    return get_auth_headers(user_id=1, role="verified_user")


@pytest.fixture
def user_client(client, user_headers):
    client.headers.update(user_headers)
    return client


@pytest.fixture
def seed_event_environment(create_model_factory):
    async def _seed(uow):
        await create_model_factory(uow, "user", id=1, email="test1@test.com", username="user1", password="pwd",
                                   role=UserRole.VERIFIED_USER)
        await create_model_factory(uow, "event_category", id=1, name="Music")

    return _seed


import uuid
from datetime import datetime, timezone, timedelta
import pytest


@pytest.fixture
def create_event() -> EventFactory:
    async def _create(
            user_id: int = 1,
            title: str | None = None,
            state: EventState = EventState.APPROVED,
            category_id: int = 1,
            format: EventFormat = EventFormat.ONLINE,
            address: str = "Address",
            started_at: datetime | None = None,
    ) -> EventDTO:
        suffix = uuid.uuid4().hex[:6]
        final_title = title or f"Event_{suffix}"

        async with create_app_uow() as uow:
            data = {
                "user_id": user_id,
                "title": final_title,
                "description": "Desc",
                "state": state,
                "category_id": category_id,
                "format": format,
                "started_at": started_at or (datetime.now(timezone.utc) + timedelta(days=1)),
            }

            if format == EventFormat.OFFLINE:
                data["address"] = address

            obj = await uow.event.create(**data)
            await uow.commit()
            return obj

    return _create


@pytest.fixture
def create_event_category() -> EventCategoryFactory:
    async def _create(
            name: str | None = None,
            parent_id: int | None = None,
    ) -> EventCategoryDTO:
        suffix = uuid.uuid4().hex[:6]
        final_name = name or f"Event Category {suffix}"

        async with create_app_uow() as uow:
            data = {"name": final_name}
            if parent_id is not None:
                data["parent_id"] = parent_id

            obj = await uow.event_category.create(**data)
            await uow.commit()
            return obj

    return _create


@pytest.fixture
def event_context(
        create_event_category: EventCategoryFactory,
        create_user: UserFactory,
) -> EventContext:
    async def _seed(
            category_name: str | None = None,
            user_email: str | None = None,
            username: str | None = None,
            user_role: UserRole = UserRole.USER,
    ) -> tuple[EventCategoryDTO, UserDTO]:
        cat_obj = await create_event_category(name=category_name)
        user_obj = await create_user(
            email=user_email,
            username=username,
            role=user_role
        )
        return cat_obj, user_obj

    return _seed


@pytest.fixture
def private_event_context(
        create_event_category: EventCategoryFactory,
        create_user: UserFactory,
        create_event: EventFactory,
) -> PrivateEventContext:
    async def _seed(
            category_name: str | None = None,
            user_email: str | None = None,
            username: str | None = None,
            event_title: str | None = None,
            event_address: str = "Address",
            event_format: EventFormat = EventFormat.ONLINE,
    ) -> tuple[EventCategoryDTO, UserDTO, EventDTO]:
        cat_obj = await create_event_category(name=category_name)
        user_obj = await create_user(
            email=user_email,
            username=username,
            role=UserRole.VERIFIED_USER,
        )
        event_obj = await create_event(
            user_id=user_obj.id,
            category_id=cat_obj.id,
            title=event_title,
            address=event_address,
            format=event_format,
        )
        return cat_obj, user_obj, event_obj

    return _seed
