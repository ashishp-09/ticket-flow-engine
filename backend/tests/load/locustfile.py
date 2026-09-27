import asyncio

from gevent import time
from gevent.queue import Empty, Queue
from locust import events, FastHttpUser

from src.app.uow import create_app_uow
from src.core.security import JWTManager
from src.core.settings import get_settings
from src.modules.user.models import UserRole
from tasks.admin import AdminBehavior
from tasks.moderator import ModeratorBehavior
from tasks.regular import RegularUserBehavior
from tasks.verified import VerifiedUserBehavior


class TestDataState:
    def __init__(self):
        self.user_pools = {role: Queue() for role in UserRole}
        self.event_categories_queue = Queue()
        self.active_events_queue = Queue()

    def get_active_event(self) -> any:
        try:
            event_id = self.active_events_queue.get_nowait()
            self.active_events_queue.put_nowait(event_id)
            return event_id
        except Empty:
            return None

    def add_active_event(self, event_id: any):
        elements = []
        while not self.active_events_queue.empty():
            elements.append(self.active_events_queue.get_nowait())
        if event_id not in elements:
            elements.append(event_id)
        for el in elements:
            self.active_events_queue.put_nowait(el)

    def remove_active_event(self, event_id: any):
        size = self.active_events_queue.qsize()
        for _ in range(size):
            try:
                current_id = self.active_events_queue.get_nowait()
                if current_id != event_id:
                    self.active_events_queue.put_nowait(current_id)
            except Empty:
                break

    def get_event_category(self) -> any:
        try:
            category_id = self.event_categories_queue.get_nowait()
            self.event_categories_queue.put_nowait(category_id)
            return category_id
        except Empty:
            return None


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    environment.state = TestDataState()
    asyncio.run(_load_bootstrap_data(environment.state))


async def _load_bootstrap_data(state: TestDataState):
    uow = create_app_uow()
    async with uow:
        for role in state.user_pools.keys():
            users = await uow.user.filter(role=role).all()
            for user in users:
                state.user_pools[role].put_nowait({
                    "id": user.id,
                    "email": user.email,
                    "password": user.password
                })

        state.active_events_queue = Queue()
        state.event_categories_queue = Queue()

        leaf_categories = await uow.event_category.filter(children__has_no=True).all()
        for c in leaf_categories:
            state.event_categories_queue.put_nowait(c.id)

        active_events = await uow.event.filter(status="upcoming").all()
        for event in active_events:
            state.active_events_queue.put_nowait(event.id)


class BaseAuthorizedUser(FastHttpUser):
    abstract = True
    role = None

    discovered_category_ids: list[int]
    created_order_ids: list[int]

    def on_start(self):
        self.discovered_category_ids = []
        self.created_order_ids = []

        state: TestDataState = self.environment.state
        try:
            self.user_data = state.user_pools[self.role].get_nowait()
            state.user_pools[self.role].put_nowait(self.user_data)
        except Empty:
            time.sleep(1)
            return self.on_start()

        config = get_settings()
        jwt_manager = JWTManager(
            secret_key=config.jwt_secret_key,
            algorithm=config.jwt_algorithm,
            expire_seconds=config.jwt_expires_in
        )

        token = jwt_manager.create_access_token(
            data={"sub": str(self.user_data["id"]), "role": self.role}
        )
        self.auth_headers = {"Authorization": f"Bearer {token}"}


class RegularUser(BaseAuthorizedUser):
    weight = 50
    role = UserRole.USER
    tasks = [RegularUserBehavior]


class VerifiedUser(BaseAuthorizedUser):
    weight = 30
    role = UserRole.VERIFIED_USER
    tasks = [VerifiedUserBehavior]


class ModeratorUser(BaseAuthorizedUser):
    weight = 15
    role = UserRole.MODERATOR
    tasks = [ModeratorBehavior]


class AdminUser(BaseAuthorizedUser):
    weight = 5
    role = UserRole.ADMIN
    tasks = [AdminBehavior]
