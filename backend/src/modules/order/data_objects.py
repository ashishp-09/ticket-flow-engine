from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from src.core.infra.database import BaseDTO

if TYPE_CHECKING:
    from src.modules.ticket.data_objects import TicketCategoryDTO
    from src.modules.user.data_objects import UserDTO


@dataclass(slots=True)
class OrderItemDTO(BaseDTO):
    id: int
    order_id: int
    category_id: int
    quantity: int
    category: Optional[TicketCategoryDTO] = None


@dataclass(slots=True)
class OrderDTO(BaseDTO):
    id: int
    user_id: Optional[int]
    anonymous_email: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemDTO] = field(default_factory=list)
    user: Optional[UserDTO] = None
