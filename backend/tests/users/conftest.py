import uuid

import pytest

from core.types import UserFactory
from src.app.uow import create_app_uow
from src.modules.user.data_objects import UserDTO
from src.modules.user.models import UserRole


@pytest.fixture
def user_headers(get_auth_headers):
    return get_auth_headers(user_id=1, role="user")


@pytest.fixture
def user_client(client, user_headers):
    client.headers.update(user_headers)
    return client


@pytest.fixture
def create_user() -> UserFactory:
    async def _create(
            email: str | None = None,
            username: str | None = None,
            role: UserRole = UserRole.USER,
    ) -> UserDTO:
        suffix = uuid.uuid4().hex[:6]
        final_email = email or f"test_{suffix}@test.com"
        final_username = username or f"test_{suffix}"

        async with create_app_uow() as uow:
            obj = await uow.user.create(
                email=final_email,
                username=final_username,
                password="pwd",
                role=role
            )
            await uow.commit()
            return obj

    return _create
