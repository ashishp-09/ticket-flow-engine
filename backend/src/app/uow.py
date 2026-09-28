from __future__ import annotations

from src.core.database import db_factory
from src.core.infra.database.exceptions.factory import create_postgres_exception_mapper
from src.core.infra.database.repositories import Repository
from src.core.infra.database.uow.units import SQLAlchemyUnitOfWork
from src.modules.event.data_objects import EventCategoryDTO, EventDTO
from src.modules.event.models import Event, EventCategory
from src.modules.order.data_objects import OrderDTO, OrderItemDTO
from src.modules.order.models import Order, OrderItem
from src.modules.ticket.data_objects import TicketCategoryDTO, TicketDTO
from src.modules.ticket.models import Ticket, TicketCategory
from src.modules.user.data_objects import UserDTO
from src.modules.user.models import User
from src.modules.views.data_objects import ViewLogDTO
from src.modules.views.models import ViewLog


class AppUnitOfWork(SQLAlchemyUnitOfWork):
    """
    Declarative Unit of Work configuration for application repositories.

    This class serves as the Single Source of Truth for both static analysis
    (IDE auto-completion, mypy/pyright) and runtime initialization.

    Strict validation rules enforced during initialization:
    - Attributes must be strictly type-hinted using the Repository[Model, DTO] marker.
    - Bare GenericRepository or raw class injections without generic arguments are forbidden.
    - Complex types like Union, Optional, or '| None' are forbidden.
    - Automatically generated repository classes are isolated and strictly unique per attribute.

    Format:
        attribute_name: Repository[Model, DTO]
    """
    user: Repository[User, UserDTO]
    event: Repository[Event, EventDTO]
    event_category: Repository[EventCategory, EventCategoryDTO]
    ticket: Repository[Ticket, TicketDTO]
    ticket_category: Repository[TicketCategory, TicketCategoryDTO]
    order: Repository[Order, OrderDTO]
    order_item: Repository[OrderItem, OrderItemDTO]
    view_logs: Repository[ViewLog, ViewLogDTO]


def create_app_uow() -> AppUnitOfWork:
    return AppUnitOfWork(
        db_factory=db_factory,
        exception_mapper=create_postgres_exception_mapper()
    )
