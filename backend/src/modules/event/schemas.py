from pydantic import AwareDatetime, Field, field_validator, model_validator

from src.core.infra.transport.http import FilterParamsSchema, GenericRequestSchema, GenericResponseSchema, \
    partial_model, PositiveInt32
from src.core.infra.transport.http.annotations import NonEmptyString
from .models import EventFormat


class EventCreateSchema(GenericRequestSchema):
    category_id: PositiveInt32 = Field(..., gt=0)
    title: NonEmptyString = Field(..., max_length=100)
    description: NonEmptyString | None = Field(None, max_length=255)
    format: EventFormat
    address: NonEmptyString | None = Field(None, max_length=255)
    started_at: AwareDatetime

    @model_validator(mode="after")
    def validate_address_based_on_type(self) -> "EventCreateSchema":
        if self.format == EventFormat.OFFLINE and (not self.address or not self.address.strip()):
            raise ValueError("'address' field is required for offline events")
        if self.format == EventFormat.ONLINE:
            self.address = None
        return self


@partial_model(EventCreateSchema)
class EventUpdateSchema(EventCreateSchema):
    pass


class EventCategoryCreateSchema(GenericRequestSchema):
    name: NonEmptyString = Field(..., max_length=100)
    parent_id: PositiveInt32 | None = None


class EventCategoryResponseSchema(GenericResponseSchema):
    id: int
    name: str
    parent_id: int | None = None
    can_create_events: bool | None = None
    can_create_subcategories: bool | None = None


class EventResponseSchema(GenericResponseSchema):
    id: int
    title: str
    user_id: int
    category_id: int
    status: str
    format: EventFormat
    started_at: AwareDatetime
    address: str | None
    views: int | None


class EventFilterParamsSchema(FilterParamsSchema):
    ORDERING_FIELDS = {"id", "title", "started_at", "status"}

    category_id: PositiveInt32 | None = None
    title__icontains: NonEmptyString | None = Field(None, max_length=100)
    format: EventFormat | None = None
    address: NonEmptyString | None = Field(None, max_length=255)
    started_at: AwareDatetime | None = None
    started_at__gte: AwareDatetime | None = None
    started_at__lte: AwareDatetime | None = None


class EventCategoryFilterParamsSchema(FilterParamsSchema):
    ORDERING_FIELDS = {"id", "name"}

    name__icontains: NonEmptyString | None = Field(None, max_length=100)
    parent_id: PositiveInt32 | None = None
    parent_id__is_null: bool | None = None
    can_create_events: bool | None = None
    can_create_subcategories: bool | None = None


class EventsByUserFilterParamsSchema(EventFilterParamsSchema):
    pass


class UpcomingEventsFilterParamsSchema(EventFilterParamsSchema):
    user_id: PositiveInt32 | None = None
