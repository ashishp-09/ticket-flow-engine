from fastapi import status
from httpx import AsyncClient, ASGITransport
import pytest

from src.app.main import app


class TestHealthEndpoints:
    async def test_healthcheck_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/healthcheck")
            assert res.status_code == status.HTTP_200_OK
            assert res.json() == {"status": "ok"}

    async def test_detailed_health_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/health")
            assert res.status_code == status.HTTP_200_OK
            data = res.json()
            assert data["status"] == "healthy"
            assert data["service"] == "ticket-flow-engine"
            assert "subsystems" in data
