from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.event.models import Event
    from src.modules.order.models import Order

from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.infra.database.orm import AbstractORMModel


class UserRole(StrEnum):
    USER = "user"
    ON_VERIFICATION = "on_verification"
    VERIFIED_USER = "verified_user"
    MODERATOR = "moderator"
    ADMIN = "admin"

    @property
    def _weight(self) -> int:
        weights = {
            UserRole.USER: 10,
            UserRole.ON_VERIFICATION: 10,
            UserRole.VERIFIED_USER: 20,
            UserRole.MODERATOR: 30,
            UserRole.ADMIN: 40,
        }
        return weights[self]

    def __lt__(self, other: "UserRole") -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        return self._weight < other._weight

    def __le__(self, other: "UserRole") -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        return self._weight <= other._weight

    def __gt__(self, other: "UserRole") -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        return self._weight > other._weight

    def __ge__(self, other: "UserRole") -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        return self._weight >= other._weight


class User(AbstractORMModel):
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False),
        index=True,
        default=UserRole.USER,
    )

    email: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    username: Mapped[str] = mapped_column(String(32), nullable=True)
    password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    events: Mapped[Event] = relationship("Event", back_populates="user")
    orders: Mapped[Order] = relationship("Order", back_populates="user")

    __table_args__ = (CheckConstraint("email LIKE '%@%.%'", name="check_email_format"),)
