from src.core.settings import get_settings
from .abstract import BasePaymentGateway
from .mock import MockPaymentGateway
from .stripe import StripePaymentGateway


class PaymentGatewayFactory:
    def __init__(self):
        self._instance: BasePaymentGateway | None = None

    def __call__(self) -> BasePaymentGateway:
        if self._instance is None:
            settings = get_settings()
            if (
                settings.testing
                or getattr(settings, "payment_gateway_mock_mode", True)
                or not getattr(settings, "stripe_secret_key", None)
            ):
                self._instance = MockPaymentGateway()
            else:
                self._instance = StripePaymentGateway(
                    api_key=getattr(settings, "stripe_secret_key", ""),
                    webhook_secret=getattr(settings, "stripe_webhook_secret", None),
                )
        return self._instance


get_payment_gateway = PaymentGatewayFactory()
