import pytest
from fastapi import status


class TestAdminSchemaAndSecurity:
    user_role = "admin"

    @pytest.mark.parametrize("url", ["/admin/categories?limit=10&offset=0", "/admin/users?limit=10&offset=0"])
    async def test_admin_pagination_schema_integrity(self, api_client, url):
        response = await api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert isinstance(data["results"], list)

    @pytest.mark.parametrize(
        "url",
        [
            "/admin/categories?limit=-1&offset=0",
            "/admin/categories?limit=10&offset=-5",
            "/admin/categories?limit=abc&offset=0",
            "/admin/categories?limit=10&offset=xyz",
            "/admin/categories?limit=10&offset=0&order_by=non_existent_column",
            "/admin/users?limit=-1&offset=0",
            "/admin/users?limit=10&offset=-5",
            "/admin/users?limit=abc&offset=0",
            "/admin/users?limit=10&offset=xyz",
            "/admin/users?limit=10&offset=0&order_by=non_existent_column",
        ],
    )
    async def test_admin_pagination_and_sorting_errors(self, api_client, url):
        response = await api_client.get(url)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestAdminEndpointsPermissions:
    user_role = "user"

    @pytest.mark.parametrize(
        "method,url,payload",
        [
            ("POST", "/admin/categories", {"name": "VIP Pass"}),
            ("GET", "/admin/categories?limit=10&offset=0", None),
            ("GET", "/admin/users?limit=10&offset=0", None),
            ("PATCH", "/admin/users/20/ban", None),
            ("PATCH", "/admin/users/30/unban", None),
        ],
    )
    async def test_admin_endpoints_forbidden_for_regular_user(self, api_client, method, url, payload):
        http_method = getattr(api_client, method.lower())
        kwargs = {}
        if payload is not None:
            kwargs["json"] = payload
        response = await http_method(url, **kwargs)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminEndpointsUnauthorized:
    @pytest.mark.parametrize(
        "method,url,payload",
        [
            ("POST", "/admin/categories", {"name": "Valid Name"}),
            ("GET", "/admin/categories", None),
            ("GET", "/admin/users", None),
            ("PATCH", "/admin/users/1/ban", None),
            ("PATCH", "/admin/users/1/unban", None),
        ],
    )
    async def test_admin_endpoints_unauthorized(self, api_client, method, url, payload):
        http_method = getattr(api_client, method.lower())
        kwargs = {"headers": {}}
        if payload is not None:
            kwargs["json"] = payload
        response = await http_method(url, **kwargs)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
