from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field


class PaymentIntentResult(BaseModel):
    id: str
    order_id: int
    amount: float
    currency: str = "USD"
    status: str
    client_secret: Optional[str] = None
    checkout_url: Optional[str] = None
    provider: str = "mock"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaymentRefundResult(BaseModel):
    id: str
    order_id: int
    amount: float
    status: str
    reason: Optional[str] = None


class BasePaymentGateway(ABC):
    @abstractmethod
    async def create_payment_intent(
        self,
        order_id: int,
        amount: float,
        currency: str = "USD",
        customer_email: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PaymentIntentResult:
        """Create a payment intent or checkout session."""
        pass

    @abstractmethod
    async def verify_webhook_event(
        self,
        payload: bytes,
        signature: Optional[str] = None,
    ) -> dict[str, Any]:
        """Verify webhook signature and return parsed event data."""
        pass

    @abstractmethod
    async def refund_payment(
        self,
        order_id: int,
        amount: float,
        reason: Optional[str] = None,
    ) -> PaymentRefundResult:
        """Process a refund for an order."""
        pass
