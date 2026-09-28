import pytest
from fastapi import status


class TestUserTicketsPagination:
    user_role = "verified_user"

    @pytest.mark.parametrize(
        "query_params",
        [
            "limit=-1&offset=0",
            "limit=10&offset=-5",
            "limit=abc&offset=0",
            "limit=10&offset=xyz",
            "limit=10&offset=0&order_by=non_existent_column",
        ],
    )
    async def test_get_my_tickets_invalid_params(self, api_client, query_params):
        response = await api_client.get(f"/tickets/my?{query_params}")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
