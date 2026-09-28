import json
import uuid
from typing import Any, Optional

from .abstract import BasePaymentGateway, PaymentIntentResult, PaymentRefundResult


class MockPaymentGateway(BasePaymentGateway):
    """
    Mock payment gateway for local development, testing, and sandbox transactions.
    """

    async def create_payment_intent(
        self,
        order_id: int,
        amount: float,
        currency: str = "USD",
        customer_email: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PaymentIntentResult:
        intent_id = f"pi_mock_{uuid.uuid4().hex[:16]}"
        client_secret = f"{intent_id}_secret_{uuid.uuid4().hex[:8]}"
        checkout_url = f"https://checkout.example.com/pay/{intent_id}?order_id={order_id}&amount={amount}"

        return PaymentIntentResult(
            id=intent_id,
            order_id=order_id,
            amount=amount,
            currency=currency,
            status="requires_payment_method",
            client_secret=client_secret,
            checkout_url=checkout_url,
            provider="mock",
            metadata=metadata or {},
        )

    async def verify_webhook_event(
        self,
        payload: bytes,
        signature: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Parses the webhook payload. For mock gateway, json deserialization is performed.
        """
        try:
            event_data = json.loads(payload.decode("utf-8"))
            return event_data
        except Exception:
            return {
                "event": "payment_intent.succeeded",
                "data": {"order_id": 0, "status": "paid"},
            }

    async def refund_payment(
        self,
        order_id: int,
        amount: float,
        reason: Optional[str] = None,
    ) -> PaymentRefundResult:
        refund_id = f"re_mock_{uuid.uuid4().hex[:16]}"
        return PaymentRefundResult(
            id=refund_id,
            order_id=order_id,
            amount=amount,
            status="succeeded",
            reason=reason or "requested_by_customer",
        )
