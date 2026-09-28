import pytest
from src.core.infra.mail.abstract import BaseEmailService
from src.core.infra.mail.factory import get_email_service
from src.core.infra.mail.mock import MockEmailService


class TestEmailInfrastructure:
    def test_mock_email_service_fallback(self):
        email_service = get_email_service()
        assert isinstance(email_service, BaseEmailService)

    async def test_mock_email_send(self):
        mock_service = MockEmailService()
        await mock_service.send(
            to_email="customer@example.com",
            subject="Test Subject",
            body="Test plain body",
        )
