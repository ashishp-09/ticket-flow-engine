from pathlib import Path
from typing import Any, Optional
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from src.core.infra.mail.abstract import BaseEmailService


class FastMailService(BaseEmailService):
    def __init__(
        self,
        username: str,
        password: str,
        mail_from: str,
        server: str,
        port: int,
        starttls: bool = True,
        ssl_tls: bool = False,
        use_credentials: bool = True,
        validate_certs: bool = True,
        template_dir: str = "templates"
    ):
        current_file_dir = Path(__file__).resolve().parent
        absolute_template_path = current_file_dir.joinpath(template_dir).resolve()

        self.config = ConnectionConfig(
            MAIL_USERNAME=username,
            MAIL_PASSWORD=password,
            MAIL_FROM=mail_from,
            MAIL_PORT=port,
            MAIL_SERVER=server,
            MAIL_STARTTLS=starttls,
            MAIL_SSL_TLS=ssl_tls,
            USE_CREDENTIALS=use_credentials,
            VALIDATE_CERTS=validate_certs,
            TEMPLATE_FOLDER=absolute_template_path,
        )
        self.fm = FastMail(self.config)

    async def send(
        self,
        to_email: str,
        subject: str,
        body: str,
        template_name: Optional[str] = None,
        lang: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        if template_name:
            localized_template = f"{lang}/{template_name}" if lang else template_name

            message = MessageSchema(
                subject=subject, recipients=[to_email], template_body=context or {}, subtype=MessageType.html
            )
            await self.fm.send_message(message, template_name=localized_template)

        else:
            message = MessageSchema(subject=subject, recipients=[to_email], body=body, subtype=MessageType.plain)
            await self.fm.send_message(message)
