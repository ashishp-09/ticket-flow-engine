from src.core.settings import get_settings
from src.core.infra.mail.abstract import BaseEmailService
from src.core.infra.mail.fast_mail import FastMailService
from src.core.infra.mail.mock import MockEmailService


class EmailServiceFactory:
    def __init__(self):
        self._instance: BaseEmailService | None = None

    def __call__(self) -> BaseEmailService:
        if self._instance is None:
            settings = get_settings()

            required_fields = [
                settings.mail_username,
                settings.mail_password,
                settings.mail_from,
                settings.mail_server,
                settings.mail_port,
            ]

            if settings.testing or not all(required_fields):
                self._instance = MockEmailService()
            else:
                self._instance = FastMailService(
                    username=settings.mail_username,
                    password=settings.mail_password,
                    mail_from=settings.mail_from,
                    server=settings.mail_server,
                    port=settings.mail_port,
                    starttls=settings.mail_starttls,
                    ssl_tls=settings.mail_ssl_tls,
                    use_credentials=settings.mail_use_credentials,
                    validate_certs=settings.mail_validate_certs,
                )

        return self._instance


get_email_service = EmailServiceFactory()
