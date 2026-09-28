from datetime import datetime
from typing import Protocol

from httpx import AsyncClient

from src.modules.event.data_objects import EventCategoryDTO, EventDTO
from src.modules.event.models import EventFormat, EventState
from src.modules.user.data_objects import UserDTO
from src.modules.user.models import UserRole


class AuthClientFactory(Protocol):
    def __call__(self, role: UserRole | None = None, user_id: int = 1) -> AsyncClient: ...


class WithRoleClient(Protocol):
    def __call__(self, role: UserRole = UserRole.USER, user_id: int = 1) -> AsyncClient: ...


class AsUserClient(Protocol):
    def __call__(self, user_id: int = 1) -> AsyncClient: ...


class AsAnonymClient(Protocol):
    def __call__(self) -> AsyncClient: ...


class EventContext(Protocol):
    async def __call__(
            self,
            category_name: str | None = None,
            user_email: str | None = None,
            username: str | None = None,
            user_role: UserRole = UserRole.USER,
    ) -> tuple[EventCategoryDTO, UserDTO]: ...


class PrivateEventContext(Protocol):
    async def __call__(
            self,
            category_name: str | None = None,
            user_email: str | None = None,
            username: str | None = None,
            event_title: str | None = None,
            event_address: str = "Address",
            event_format: EventFormat = EventFormat.ONLINE,
    ) -> tuple[EventCategoryDTO, UserDTO, EventDTO]: ...


class EventFactory(Protocol):
    async def __call__(
            self,
            user_id: int = 1,
            title: str | None = None,
            state: EventState = EventState.APPROVED,
            category_id: int = 1,
            format: EventFormat = EventFormat.ONLINE,
            address: str = "Address",
            started_at: datetime | None = None,
    ) -> EventDTO: ...


class EventCategoryFactory(Protocol):
    async def __call__(
            self,
            name: str | None = None,
            parent_id: int | None = None
    ) -> EventCategoryDTO: ...


class UserFactory(Protocol):
    async def __call__(
            self,
            email: str | None = None,
            username: str | None = None,
            role: UserRole = UserRole.USER,
    ) -> UserDTO: ...
