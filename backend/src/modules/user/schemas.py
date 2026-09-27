from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.core.infra.transport.http import FilterParamsSchema, GenericRequestSchema, GenericResponseSchema
from .models import UserRole


class BaseUserSchema(GenericRequestSchema):
    email: EmailStr = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=20)

    @field_validator("*", mode="before")
    @classmethod
    def strip_and_check_whitespaces(cls, v: any) -> any:
        if isinstance(v, str):
            v = v.strip()
        return v


class UserCreateSchema(BaseUserSchema):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)


class UserCreateResponseSchema(GenericResponseSchema):
    id: int
    email: str


class UserLoginSchema(BaseUserSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponseSchema(GenericResponseSchema):
    id: int
    email: Optional[EmailStr] = None
    role: UserRole
    username: Optional[str] = None
    is_active: bool


class UsersFilterParamsSchema(FilterParamsSchema):
    role: Optional[UserRole] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50, strip_whitespace=True)
    is_active: Optional[bool] = None

    @field_validator("username")
    @classmethod
    def validate_username_filter(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Username filter cannot be empty")
        return v
