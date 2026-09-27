import pytest
from fastapi import status


class TestModerationEndpointsPermissions:
    user_role = "user"

    @pytest.mark.parametrize(
        "method,url,payload",
        [
            ("GET", "/moderation/events?limit=10&offset=0", None),
            ("PATCH", "/moderation/events/1", {"result": True}),
            ("GET", "/moderation/users?limit=10&offset=0", None),
            ("PATCH", "/moderation/users/10", {"result": True}),
        ],
    )
    async def test_moderation_endpoints_forbidden_for_regular_user(
            self, api_client, setup_uow, create_model_factory, method, url, payload
    ):
        async with setup_uow as uow:
            await create_model_factory(uow, "user", id=1, email="user@test.com", username="user", password="pwd")
            await uow.commit()

        http_method = getattr(api_client, method.lower())

        kwargs = {}
        if payload is not None:
            kwargs["json"] = payload

        response = await http_method(url, **kwargs)

        assert response.status_code == status.HTTP_403_FORBIDDEN
