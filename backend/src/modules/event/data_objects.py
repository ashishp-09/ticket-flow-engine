from dataclasses import dataclass
from datetime import datetime

from src.core.infra.database import BaseDTO
from .models import EventState, EventStatus, EventFormat


@dataclass(frozen=True)
class EventCategoryDTO(BaseDTO):
    id: int
    name: str
    parent_id: int | None = None

    can_create_events: bool = False
    can_create_subcategories: bool = False


@dataclass
class EventDTO(BaseDTO):
    id: int
    title: str
    description: str
    user_id: int
    category_id: int
    state: EventState
    status: EventStatus
    format: EventFormat
    started_at: datetime
    address: str | None = None
    views: int = 0
