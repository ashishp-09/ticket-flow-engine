import pytest
from fastapi import status


class TestUserVerificationApply:
    user_role = "user"

    async def test_apply_for_verification_success(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="user@test.com", username="tester", password="pwd")
            await uow.commit()

        response = await api_client.post("/users/verification/apply")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_apply_for_verification_unauthorized(self, client):
        response = await client.post("/users/verification/apply", headers={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("initial_role", ["verified_user"])
    async def test_apply_for_verification_invalid_initial_role(
        self, get_auth_headers, api_client, setup_uow, create_model_factory, initial_role
    ):
        async with setup_uow as uow:
            await create_model_factory(
                uow, "user", id=10, email="role_test@test.com", username="role_user", password="pwd", role=initial_role
            )
            await uow.commit()

        headers = get_auth_headers(user_id=10, role=initial_role)
        response = await api_client.post("/users/verification/apply", headers=headers)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_apply_for_verification_user_not_found(self, get_auth_headers, api_client):
        headers = get_auth_headers(user_id=9999, role="user")
        response = await api_client.post("/users/verification/apply", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_apply_for_verification_banned_user_fails(self, get_auth_headers, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(
                uow,
                "user",
                id=15,
                email="banned_apply@test.com",
                username="banned_apply_user",
                password="pwd",
                is_active=False,
            )
            await uow.commit()

        headers = get_auth_headers(user_id=15, role="user")
        response = await api_client.post("/users/verification/apply", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
