import pytest
from fastapi import status

from src.modules.user.models import UserRole


class TestGetMe:
    user_role = UserRole.USER

    async def test_get_me_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(
                uow,
                "user",
                id=1,
                email="currentuser@example.com",
                username="currentuser",
                password="hashed_password",
                role=UserRole.USER,
                is_active=True,
            )
            await uow.commit()

        response = await api_client.get("/users/me")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["email"] == "currentuser@example.com"
        assert data["username"] == "currentuser"
        assert data["role"] == UserRole.USER
        assert data["is_active"] is True

    async def test_get_me_unauthorized(self, unauth_client):
        response = await unauth_client.get("/users/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
