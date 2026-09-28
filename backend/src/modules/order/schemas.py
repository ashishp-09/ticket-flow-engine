from datetime import datetime
from typing import Any, Optional

from pydantic import computed_field, EmailStr, Field

from src.core.infra.transport.http import FilterParamsSchema, GenericRequestSchema, GenericResponseSchema, PositiveInt32
from .models import OrderStatus


class OrderItemCreateSchema(GenericRequestSchema):
    category_id: PositiveInt32
    quantity: PositiveInt32


class OrderCreateSchema(GenericRequestSchema):
    anonymous_email: EmailStr | None = None
    items: list[OrderItemCreateSchema] = Field(..., min_length=1)


class OrderItemResponseSchema(GenericResponseSchema):
    id: int
    category_id: int
    quantity: int
    order_id: int
    purchase_price: Optional[float] = None


class OrderResponseSchema(GenericResponseSchema):
    id: int
    user_id: int | None = None
    anonymous_email: EmailStr | None = None
    status: OrderStatus
    items: list[OrderItemResponseSchema]

    @computed_field
    @property
    def total_price(self) -> float:
        return sum((item.purchase_price or 0.0) * item.quantity for item in self.items)


class OrderFilterParamsSchema(FilterParamsSchema):
    status: OrderStatus | None = None


class OrderItemFilterParamsSchema(FilterParamsSchema):
    order_id: PositiveInt32 | None = None
    order_status: OrderStatus | None = None
    category_id: PositiveInt32 | None = None
    quantity: PositiveInt32 | None = None


class OrderEmailItemSchema(GenericResponseSchema):
    category_name: str
    price_paid: float
    quantity: int


class OrderEmailDataSchema(GenericResponseSchema):
    order_id: int = Field()
    created_at: datetime
    user_email: str = Field()

    event_title: str = Field()
    event_started_at: Optional[datetime] = Field(default=None)
    event_address: str | None = Field(default=None)

    items: list[OrderEmailItemSchema]
    refund_issued: bool = Field(default=False)

    @computed_field
    @property
    def total_price(self) -> float:
        return sum(item.price_paid * item.quantity for item in self.items)


class PaymentSessionCreateSchema(GenericRequestSchema):
    currency: str = Field(default="USD", max_length=3)
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class PaymentSessionResponseSchema(GenericResponseSchema):
    order_id: int
    payment_intent_id: str
    amount: float
    currency: str = "USD"
    status: str
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    provider: str = "mock"


class OrderCancelResponseSchema(GenericResponseSchema):
    order_id: int
    status: OrderStatus
    refund_issued: bool
    message: str


class PaymentWebhookPayloadSchema(GenericRequestSchema):
    event: str
    data: dict[str, Any]
