import pytest
from src.core.infra.payment.abstract import BasePaymentGateway
from src.core.infra.payment.factory import get_payment_gateway
from src.core.infra.payment.mock import MockPaymentGateway
from src.core.infra.payment.stripe import StripePaymentGateway


class TestPaymentGateway:
    def test_payment_gateway_factory(self):
        gateway = get_payment_gateway()
        assert isinstance(gateway, BasePaymentGateway)

    async def test_mock_gateway_create_payment_intent(self):
        gateway = MockPaymentGateway()
        result = await gateway.create_payment_intent(
            order_id=42,
            amount=150.0,
            currency="USD",
            customer_email="buyer@example.com",
            description="Test Ticket Purchase",
        )
        assert result.order_id == 42
        assert result.amount == 150.0
        assert result.currency == "USD"
        assert result.provider == "mock"
        assert result.status == "requires_payment_method"
        assert result.client_secret is not None
        assert "42" in (result.checkout_url or "")

    async def test_mock_gateway_verify_webhook(self):
        gateway = MockPaymentGateway()
        raw_payload = b'{"event": "payment_intent.succeeded", "data": {"order_id": 42}}'
        event = await gateway.verify_webhook_event(payload=raw_payload)
        assert event["event"] == "payment_intent.succeeded"
        assert event["data"]["order_id"] == 42

    async def test_mock_gateway_refund(self):
        gateway = MockPaymentGateway()
        refund = await gateway.refund_payment(order_id=42, amount=150.0, reason="customer_cancellation")
        assert refund.order_id == 42
        assert refund.amount == 150.0
        assert refund.status == "succeeded"
        assert refund.reason == "customer_cancellation"

    async def test_stripe_gateway_fallback(self):
        gateway = StripePaymentGateway(api_key="sk_test_mock_dummy")
        result = await gateway.create_payment_intent(
            order_id=99,
            amount=50.0,
            currency="usd",
        )
        assert result.order_id == 99
        assert result.amount == 50.0
        assert result.provider == "stripe"
