from typing import Optional
from pydantic import EmailStr, Field, field_validator

from src.core.infra.transport.http import FilterParamsSchema, GenericRequestSchema, GenericResponseSchema, \
    partial_model, PositiveInt32
from .models import TicketStatus


class TicketCreateSchema(GenericRequestSchema):
    category_id: PositiveInt32


class TicketCategoryBaseRequestSchema(GenericRequestSchema):
    name: str = Field(..., min_length=1, max_length=255)
    price: PositiveInt32
    total_quantity: PositiveInt32

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be empty.")
        return normalized


class TicketCategoryCreateSchema(TicketCategoryBaseRequestSchema):
    event_id: PositiveInt32


@partial_model(TicketCategoryBaseRequestSchema)
class TicketCategoryUpdateSchema(TicketCategoryBaseRequestSchema):
    pass


class TicketCategoryResponseSchema(GenericResponseSchema):
    id: int
    event_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., gt=0)
    total_quantity: Optional[int] = None
    available_quantity: Optional[int] = None


class TicketResponseSchema(GenericResponseSchema):
    id: int
    category_id: Optional[int] = None
    order_item_id: Optional[int] = None
    status: Optional[TicketStatus] = None


class TicketDetailResponseSchema(GenericResponseSchema):
    id: int
    category_id: int
    status: TicketStatus
    event_id: Optional[int] = None
    event_title: Optional[str] = None
    category_name: Optional[str] = None
    price: Optional[float] = None


class TicketCheckInResponseSchema(GenericResponseSchema):
    ticket_id: int
    status: TicketStatus
    message: str


class TicketTransferSchema(GenericRequestSchema):
    target_email: EmailStr


class TicketTransferResponseSchema(GenericResponseSchema):
    ticket_id: int
    target_email: str
    message: str


class BaseTicketsFilterParamsSchema(FilterParamsSchema):
    category_id: PositiveInt32 | None = None
    price__gte: PositiveInt32 | None = None
    price__lte: PositiveInt32 | None = None

    @field_validator("price__gte", "price__lte")
    @classmethod
    def validate_prices(cls, v: int | None) -> int | None:
        if v is not None and v > 100_000_000:
            raise ValueError("Price value is realistically too high")
        return v


class TicketsFilterParamsSchema(BaseTicketsFilterParamsSchema):
    event_id: PositiveInt32 | None = Field(None, description="Event id")


class TicketsByEventFilterParamsSchema(BaseTicketsFilterParamsSchema):
    status: TicketStatus | None = Field(None, description="Ticket status")


class TicketCategoryFilterParamsSchema(BaseTicketsFilterParamsSchema):
    name__icontains: str | None = None

    available_quantity__gte: PositiveInt32 | None = None
    available_quantity__lte: PositiveInt32 | None = None
