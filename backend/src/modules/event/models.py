from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.hybrid import hybrid_property

if TYPE_CHECKING:
    from src.modules.user.models import User

from sqlalchemy import DateTime, ForeignKey, String, case, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.infra.database.orm import AbstractORMModel


class EventCategory(AbstractORMModel):
    name: Mapped[str] = mapped_column(String(100), unique=True)

    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("event_categories.id", ondelete="CASCADE"))
    parent: Mapped[Optional["EventCategory"]] = relationship(
        "EventCategory", remote_side="EventCategory.id", back_populates="children"
    )

    children: Mapped[list["EventCategory"]] = relationship(
        "EventCategory", back_populates="parent", cascade="all, delete-orphan"
    )

    events: Mapped[list["Event"]] = relationship("Event", back_populates="category")


class EventFormat(StrEnum):
    OFFLINE = "offline"
    ONLINE = "online"


class EventState(StrEnum):
    DRAFT = "draft"
    ON_MODERATION = "on_moderation"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class EventStatus(StrEnum):
    DRAFT = "draft"
    ON_MODERATION = "on_moderation"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    PAST = "past"
    UPCOMING = "upcoming"


class Event(AbstractORMModel):
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user: Mapped[User] = relationship("User", back_populates="events")

    category: Mapped[EventCategory] = relationship("EventCategory", back_populates="events")
    category_id: Mapped[int] = mapped_column(ForeignKey("event_categories.id", ondelete="RESTRICT"), index=True)

    state: Mapped[EventState] = mapped_column(
        SQLEnum(EventState, native_enum=False, length=20), default=EventState.DRAFT, index=True
    )

    format: Mapped[EventFormat] = mapped_column(SQLEnum(EventFormat, native_enum=False, length=20), index=True)

    address: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    ticket_categories = relationship("TicketCategory", back_populates="event")

    @hybrid_property
    def status(self) -> EventStatus:
        if self.state == EventState.DRAFT:
            return EventStatus.DRAFT
        if self.state == EventState.ON_MODERATION:
            return EventStatus.ON_MODERATION
        if self.state == EventState.REJECTED:
            return EventStatus.REJECTED
        if self.state == EventState.CANCELLED:
            return EventStatus.CANCELLED

        if self.started_at < datetime.now(timezone.utc):
            return EventStatus.PAST
        return EventStatus.UPCOMING

    @status.inplace.expression
    @classmethod
    def _status_expression(cls):
        return case(
            (cls.state == EventState.DRAFT, EventStatus.DRAFT.value),
            (cls.state == EventState.ON_MODERATION, EventStatus.ON_MODERATION.value),
            (cls.state == EventState.REJECTED, EventStatus.REJECTED.value),
            (cls.state == EventState.CANCELLED, EventStatus.CANCELLED.value),
            (cls.started_at < func.now(), EventStatus.PAST.value),
            else_=EventStatus.UPCOMING.value,
        )
