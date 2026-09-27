import pytest


@pytest.fixture
def admin_headers(get_auth_headers):
    return get_auth_headers(user_id=1, role="admin")


@pytest.fixture
def admin_client(client, admin_headers):
    client.headers.update(admin_headers)
    return client


@pytest.fixture
def user_headers(get_auth_headers):
    return get_auth_headers(user_id=2, role="user")
