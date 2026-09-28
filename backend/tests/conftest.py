import asyncio
import importlib
import random
from pathlib import Path

import pytest
from faststream.kafka import TestKafkaBroker
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from taskiq import InMemoryBroker

from core.types import AsAnonymClient, AsUserClient, AuthClientFactory, WithRoleClient
from src.app.uow import create_app_uow
from src.core.database import db_factory
from src.core.infra.cache.factory import get_cache_manager
from src.core.infra.database.orm.base import AbstractORMModel
from src.core.infra.transport.http.dependencies import get_jwt_manager, get_password_manager
from src.core.security import JWTManager
from src.core.settings import AppConfig, get_settings
from src.modules.user.models import UserRole
from src.workers.view_logs.main import broker

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"


def import_all_tasks() -> None:
    modules_dir = SRC_DIR / "modules"

    for tasks_file in modules_dir.glob("**/tasks.py"):
        relative_path = tasks_file.relative_to(BASE_DIR)
        module_name = ".".join(relative_path.with_suffix("").parts)
        importlib.import_module(module_name)


import_all_tasks()

test_config = AppConfig(
    testing=True,
    jwt_secret_key="test_secret_key_for_jwt_token_validation_32_chars",
    metrics_token="test_metrics_token_for_prometheus_monitoring"
)

jwt_manager = JWTManager(
    secret_key=test_config.jwt_secret_key,
    algorithm=test_config.jwt_algorithm,
    expire_seconds=test_config.jwt_expires_in,
)

from src.core.infra.cache.managers import InMemoryCacheManager

shared_test_cache = InMemoryCacheManager()
get_cache_manager._instance = shared_test_cache


@pytest.fixture(autouse=True)
async def setup_taskiq():
    if isinstance(broker, InMemoryBroker):
        broker.await_inplace = True

    yield

    if isinstance(broker, InMemoryBroker):
        await asyncio.sleep(0)
        broker.await_inplace = False
        broker.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def clean_db():
    await asyncio.sleep(0.05)

    await shared_test_cache.clear()

    try:
        engine = db_factory.get_engine()
        async with engine.begin() as conn:
            table_names = [table.name for table in reversed(AbstractORMModel.metadata.sorted_tables)]
            joined_tables = ", ".join(f'"{name}"' for name in table_names)
            await conn.execute(text(f"TRUNCATE TABLE {joined_tables} RESTART IDENTITY CASCADE;"))
    except Exception:
        pass


@pytest.fixture(scope="session")
def get_auth_headers():
    def _get_headers(user_id: int | str, role: str | UserRole) -> dict[str, str]:
        token = jwt_manager.create_access_token(data={"sub": str(user_id), "role": str(role)})
        return {"Authorization": f"Bearer {token}"}

    return _get_headers


@pytest.fixture(autouse=True)
def setup_global_overrides():
    from src.app.main import app

    app.dependency_overrides[get_settings] = lambda: test_config
    app.dependency_overrides[get_jwt_manager] = lambda: jwt_manager

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def setup_uow(setup_global_overrides):
    from src.app.main import app
    test_uow = create_app_uow()

    yield test_uow

    app.dependency_overrides[get_settings] = lambda: test_config


@pytest.fixture(scope="session")
def pwd_manager():
    return get_password_manager()


@pytest.fixture(scope="session")
def api_transport():
    from src.app.main import app
    return ASGITransport(app=app)


@pytest.fixture
async def client(api_transport):
    async with AsyncClient(transport=api_transport, base_url="http://test/api/v1") as ac:
        yield ac


@pytest.fixture
def create_model_factory():
    async def _create(uow, repo_attr, **kwargs):
        repo = getattr(uow, repo_attr)
        obj = await repo.create(**kwargs)
        await uow.flush()
        return obj

    return _create


@pytest.fixture
async def api_client(client, request, get_auth_headers):
    user_role = getattr(request.cls, "user_role", None) or getattr(request.function, "user_role", None)
    user_id = getattr(request.cls, "user_id", 1)

    if user_role:
        headers = get_auth_headers(user_id=user_id, role=user_role)
        client.headers.update(headers)
    else:
        client.headers.pop("Authorization", None)

    return client


@pytest.fixture
def auth_client_factory(api_transport, get_auth_headers) -> AuthClientFactory:
    def _create_client(role: UserRole | None = None, user_id: int = 1) -> AsyncClient:
        fake_ip = f"{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
        fake_ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestBrowser/{random.randint(100, 999)}"

        headers = {
            "X-Forwarded-For": fake_ip,
            "User-Agent": fake_ua,
        }

        if role is not None:
            headers.update(get_auth_headers(user_id=user_id, role=role))

        return AsyncClient(
            transport=api_transport,
            base_url="http://test/api/v1",
            headers=headers
        )

    return _create_client


@pytest.fixture
def with_role(auth_client_factory) -> WithRoleClient:
    def _with_role(role: UserRole = UserRole.USER, user_id: int = 1) -> AsyncClient:
        return auth_client_factory(role=role, user_id=user_id)

    return _with_role


@pytest.fixture
def as_anonym(auth_client_factory) -> AsAnonymClient:
    def _as_anonym() -> AsyncClient:
        return auth_client_factory(role=None)

    return _as_anonym


@pytest.fixture
def as_user(auth_client_factory) -> AsUserClient:
    def _as_user(user_id: int = 1) -> AsyncClient:
        return auth_client_factory(role=UserRole.USER, user_id=user_id)

    return _as_user


@pytest.fixture
def as_verified_user(auth_client_factory) -> AsUserClient:
    def _as_verified_user(user_id: int = 1) -> AsyncClient:
        return auth_client_factory(role=UserRole.VERIFIED_USER, user_id=user_id)

    return _as_verified_user


@pytest.fixture
def as_moderator(auth_client_factory) -> AsUserClient:
    def _as_moderator(user_id: int = 1) -> AsyncClient:
        return auth_client_factory(role=UserRole.MODERATOR, user_id=user_id)

    return _as_moderator


@pytest.fixture
async def mock_kafka() -> TestKafkaBroker:
    async with TestKafkaBroker(broker) as br:
        yield br


pytest_plugins = ["users.conftest"]
