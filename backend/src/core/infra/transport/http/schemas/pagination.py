from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from .generic import GenericRequestSchema


class PaginatedResponseSchema[T](BaseModel):
    count: int
    max_pages: int
    results: list[T]


class PaginationParamsSchema(GenericRequestSchema):
    limit: int = Field(default=10, ge=1, le=100, description="Amount of records to return per page.")
    offset: int = Field(default=0, ge=0, description="How many elements to skip.")


class FilterParamsSchema(PaginationParamsSchema):
    order_by: str | None = Field(
        default=None,
        description="Field to sort by. The '-' sign before the name means DESC.",
        max_length=100
    )

    ORDERING_FIELDS: ClassVar[set[str]] = set()
    _BASE_FIELDS = {"limit", "offset", "order_by"}

    @field_validator("order_by")
    @classmethod
    def validate_order_by(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.lstrip("-").strip()
            if not cleaned or not cleaned.isidentifier():
                raise ValueError("Invalid order_by field name format")

            if cls.ORDERING_FIELDS and cleaned not in cls.ORDERING_FIELDS:
                raise ValueError(
                    f"Sorting by '{cleaned}' is not allowed. "
                    f"Allowed fields: {', '.join(sorted(cls.ORDERING_FIELDS))}"
                )
        return v

    @property
    def specific_filters(self) -> dict[str, Any]:
        full_data = self.model_dump(exclude_none=True)
        return {
            k: v for k, v in full_data.items()
            if k not in self._BASE_FIELDS
        }
