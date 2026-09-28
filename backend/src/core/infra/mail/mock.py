from typing import Any, Optional

from src.core.infra.mail.abstract import BaseEmailService


class MockEmailService(BaseEmailService):
    async def send(
        self,
        to_email: Optional[str],
        subject: Optional[str],
        body: str,
        template_name: Optional[str] = None,
        lang: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        pass
