import pytest
from fastapi import status


class TestUserAuth:
    async def test_register_success(self, api_client):
        payload = {"email": "register_test@example.com", "username": "tester", "password": "securepassword123"}
        response = await api_client.post("/users", json=payload)
        res_data = response.json()
        assert response.status_code == status.HTTP_201_CREATED
        assert isinstance(res_data.get("id"), int)
        assert res_data.get("email") == payload["email"]

    @pytest.mark.parametrize(
        "payload",
        [
            {"email": "not-an-email", "username": "te", "password": "123"},
            {"email": "whitespace@test.com", "username": "   ", "password": "securepassword123"},
        ],
    )
    async def test_register_invalid_data(self, api_client, payload):
        response = await api_client.post("/users", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_register_duplicate_email(self, api_client, setup_uow, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(
                uow, "user", email="duplicate@example.com", username="existing_user", password="somepassword"
            )
            await uow.commit()

        payload = {"email": "duplicate@example.com", "username": "new_user", "password": "securepassword123"}
        response = await api_client.post("/users", json=payload)
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_login_success(self, api_client, setup_uow, pwd_manager, create_model_factory):
        hashed_password = await pwd_manager.hash_password("correct_password")
        async with setup_uow as uow:
            await create_model_factory(
                uow, "user", email="login_test@example.com", username="login_tester", password=hashed_password
            )
            await uow.commit()

        payload_login = {"email": "login_test@example.com", "password": "correct_password"}
        response = await api_client.post("/users/login", json=payload_login)
        res_data = response.json()
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in res_data
        assert res_data.get("token_type") == "bearer"

    @pytest.mark.parametrize(
        "email, password, expected_status",
        [
            ("wrong_pwd@example.com", "incorrect_password", status.HTTP_401_UNAUTHORIZED),
            ("nonexistent@example.com", "any_password", status.HTTP_401_UNAUTHORIZED),
        ],
    )
    async def test_login_failed_scenarios(self, api_client, setup_uow, create_model_factory, email, password, expected_status):
        async with setup_uow as uow:
            await create_model_factory(
                uow, "user", email="wrong_pwd@example.com", username="pwd_tester", password="hashed_correct_password"
            )
            await uow.commit()

        payload_login = {"email": email, "password": password}
        response = await api_client.post("/users/login", json=payload_login)
        assert response.status_code == expected_status

    async def test_login_invalid_data(self, api_client):
        payload_login = {"email": "not-an-email", "password": ""}
        response = await api_client.post("/users/login", json=payload_login)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_login_banned_user_fails(self, api_client, setup_uow, pwd_manager, create_model_factory):
        async with setup_uow as uow:
            await create_model_factory(
                uow,
                "user",
                id=16,
                email="banned_login@test.com",
                username="banned_login_user",
                password=await pwd_manager.hash_password("securepassword123"),
                is_active=False,
            )
            await uow.commit()

        payload = {"email": "banned_login@test.com", "password": "securepassword123"}
        response = await api_client.post("/users/login", json=payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN
