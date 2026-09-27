import pytest
from fastapi import status


class TestModeratorUsers:
    user_role = "moderator"

    async def test_get_users_for_verification_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(
                uow, "user", id=10, email="user@test.com", username="user", password="pwd", role="on_verification"
            )
            await uow.commit()

        response = await api_client.get("/moderation/users")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"][0]["id"] == 10

    @pytest.mark.parametrize("result", [True, False])
    async def test_moderate_user_success(self, api_client, setup_uow, create_model_factory, result):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(
                uow,
                "user",
                id=10,
                email="mod_target@test.com",
                username="mod_user",
                password="hash_password",
                role="on_verification",
            )
            await uow.commit()

        response = await api_client.patch("/moderation/users/10", json={"result": result})
        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = await api_client.get("/moderation/users")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["count"] == 0

    async def test_moderate_user_without_application_fails(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await create_model_factory(
                uow, "user", id=10, email="no_app@test.com", username="no_app_user", password="pwd", role="user"
            )
            await uow.commit()

        response = await api_client.patch("/moderation/users/10", json={"result": True})
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_moderate_user_not_found(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=2, email="mod@test.com", username="mod", password="pwd")
            await uow.commit()

        response = await api_client.patch("/moderation/users/2147483646", json={"result": True})
        assert response.status_code == status.HTTP_404_NOT_FOUND
