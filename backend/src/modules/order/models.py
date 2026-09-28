from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.modules.ticket.models import Ticket, TicketCategory
    from src.modules.user.models import User

from enum import StrEnum
from typing import Optional

from sqlalchemy import ForeignKey, String, Enum as SQLEnum, CheckConstraint, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.infra.database.orm import AbstractORMModel


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class Order(AbstractORMModel):
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
                                                   index=True)
    user: Mapped[User] = relationship("User", back_populates="orders")
    anonymous_email: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, native_enum=False), index=True, default=OrderStatus.PENDING
    )

    items: Mapped[list[OrderItem]] = relationship("OrderItem", back_populates="order")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NULL AND anonymous_email IS NULL) OR "
            "(user_id IS NOT NULL AND anonymous_email IS NULL) OR "
            "(user_id IS NULL AND anonymous_email IS NOT NULL)",
            name="check_order_owner",
        ),
    )


class OrderItem(AbstractORMModel):
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    order: Mapped[Order] = relationship("Order", back_populates="items")

    category_id: Mapped[int] = mapped_column(ForeignKey("ticket_categories.id", ondelete="RESTRICT"), index=True)
    category: Mapped[TicketCategory] = relationship("TicketCategory")

    quantity: Mapped[int] = mapped_column(Integer)

    purchase_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    tickets: Mapped[list[Ticket]] = relationship("Ticket", back_populates="order_item")
