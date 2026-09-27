import random
import secrets
from datetime import datetime, timedelta, timezone

from src.cli.base import BaseCommand
from src.cli.colors import CLR_CYAN, CLR_MAGENTA, CLR_RESET
from src.core.infra.database.uow.units import SQLAlchemyUnitOfWork
from src.core.security.passwords import PasswordManager
from src.core.settings import get_settings
from src.modules.event.models import EventFormat, EventState
from src.modules.order.models import OrderStatus
from src.modules.user.models import UserRole

CATEGORIES_POOL = {
    "Музыка": ["Рок и Альтернатива", "Джаз и Блюз", "Электронная музыка", "Классика в соборе", "Поп-хиты"],
    "Театр и Кино": ["Драматические спектакли", "Опера и Балет", "Иммерсивные шоу", "Артхаус показы", "Мюзиклы"],
    "Образование": ["IT-Конференции", "Бизнес-интенсивы", "Лекции по искусству", "Языковые клубы", "Хакатоны"],
    "Спорт": ["Футбольные матчи", "Марафоны и Бег", "Турниры по теннису", "Экстремальный спорт", "Киберспорт"],
    "Развлечения": ["Стендап шоу", "Гастро-фестивали", "Квизы и Настолки", "Ночные маркеты", "Выставки комиксов"]
}

EVENT_ADJECTIVES = ["Грандиозный", "Камерный", "Ежегодный", "Международный", "Секретный", "Благотворительный",
                    "Юбилейный"]
EVENT_NOUNS = ["Фестиваль", "Воркшоп", "Перформанс", "Концерт", "Турнир", "Симпозиум", "Рейв", "Слёт"]

CITIES_POOL = [
    "Москва, Парк Горького", "Санкт-Петербург, Севкабель Порт", "Казань, Кремлевская набережная",
    "Екатеринбург, Ельцин Центр", "Новосибирск, Лофт Квадрат", "Сочи, Олимпийский Парк"
]

TICKET_NAMES_POOL = ["Standard Pass", "VIP Box", "Early Bird", "Fan Zone", "Student Ticket"]
PRICES_POOL = [490.0, 1500.0, 2900.0, 5500.0, 9900.0]

FIRST_NAMES = ["Иван", "Анна", "Сергей", "Мария", "Александр", "Елена", "Дмитрий", "Ольга"]
LAST_NAMES = ["Петров", "Иванова", "Смирнов", "Кузнецова", "Попов", "Васильева"]


class SeedCommand(BaseCommand):
    name = "seed"
    description = "Fill database with randomized demonstration data"

    def __init__(self) -> None:
        super().__init__()
        self.config = get_settings()
        self.pwd_manager = PasswordManager(
            algorithm=self.config.password_algorithm,
            iterations=self.config.password_iterations
        )
        self.allowed_event_hosts = []
        self.regular_buyers = []
        self.all_user_ids = []
        self.leaf_category_ids = []
        self.all_event_ids = []
        self.purchasable_ticket_categories = []

    def parse_args(self, args: list[str]) -> dict:
        params = {"users_count": 34, "events_count": 100, "orders_count": 150, "clean": False}
        if "--clean" in args:
            params["clean"] = True
        mapping = {"--users": "users_count", "--events": "events_count", "--orders": "orders_count"}
        for flag, key in mapping.items():
            if flag in args:
                try:
                    idx = args.index(flag)
                    params[key] = int(args[idx + 1])
                except (ValueError, IndexError):
                    raise ValueError(f"Flag {flag} requires an integer value.")
        return params

    async def handle(self, uow: SQLAlchemyUnitOfWork, **options) -> None:
        users_count = options["users_count"]
        events_count = options["events_count"]
        orders_count = options["orders_count"]
        should_clean = options["clean"]

        pipeline = []
        if should_clean:
            pipeline.append(("clean", "Truncate existing database tables and sequences"))
        pipeline.extend([
            ("users", "Create demonstration users and roles hierarchy"),
            ("categories", "Build multi-level event categories structure"),
            ("events", "Generate historical and upcoming event baselines"),
            ("orders", "Process customer orders and emission workflows"),
            ("views", "Collect anonymous and user unique view logs")
        ])
        self.set_pipeline(pipeline)

        if should_clean:
            self.start_step("clean")
            await self._clean_tables(uow)

        self.start_step("users")
        await self._seed_admin(uow)
        await self._seed_users(uow, users_count)

        self.start_step("categories")
        await self._seed_categories(uow)

        self.start_step("events")
        await self._seed_events(uow, events_count)

        self.start_step("orders")
        await self._seed_orders(uow, orders_count)

        self.start_step("views")
        await self._seed_view_logs(uow)

        await uow.commit()

        self._print_dashboard(users_count, events_count, orders_count)

    async def _clean_tables(self, uow: SQLAlchemyUnitOfWork) -> None:
        from sqlalchemy import text
        repos = [uow.view_logs, uow.order_item, uow.order, uow.ticket_category, uow.event, uow.event_category, uow.user]
        for idx, repo in enumerate(repos, 1):
            table_name = repo.get_model_name()
            self.update_sub(f"Truncating {table_name} ({idx}/{len(repos)})...")
            await uow._session.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))

    async def _seed_admin(self, uow: SQLAlchemyUnitOfWork) -> None:
        admin_raw_password = "".join(
            random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$", k=14)
        )
        admin_hashed_password = await self.pwd_manager.hash_password(admin_raw_password)
        admin_obj = await uow.user.get(email="admin@test.ru")
        if admin_obj is None:
            admin_obj = await uow.user.create(
                email="admin@test.ru",
                username="system_admin",
                password=admin_hashed_password,
                role=UserRole.ADMIN,
                is_active=True
            )
            self.print_raw_log(
                f"{CLR_MAGENTA}[ADMIN CREATED] Email: admin@test.ru | Password: {admin_raw_password}{CLR_RESET}")
        if admin_obj and hasattr(admin_obj, "id"):
            self.allowed_event_hosts.append(admin_obj.id)
            self.all_user_ids.append(admin_obj.id)

    async def _seed_users(self, uow: SQLAlchemyUnitOfWork, count: int) -> None:
        self.print_raw_log("-" * 80)
        self.print_raw_log(f"{CLR_CYAN}{'ROLE':<18} | {'EMAIL':<30}{CLR_RESET}")
        self.print_raw_log("-" * 80)

        bulk_users = []
        used_emails = set()
        sample_buyer_email = None
        sample_host_email = None

        runtime_raw_password = "".join(
            random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$", k=14)
        )
        runtime_hashed_password = await self.pwd_manager.hash_password(runtime_raw_password)

        for i in range(1, count + 1):
            f_name = random.choice(FIRST_NAMES)
            l_name = random.choice(LAST_NAMES)
            username = f"{f_name.lower()}_{l_name.lower()}_{random.randint(10, 9999)}"
            email = f"{username}@test.ru"
            if email in used_emails:
                continue
            used_emails.add(email)

            role = random.choice([UserRole.USER, UserRole.VERIFIED_USER, UserRole.ON_VERIFICATION, UserRole.MODERATOR])
            bulk_users.append({
                "email": email,
                "username": username,
                "password": runtime_hashed_password,
                "role": role,
                "is_active": True
            })

            if role == UserRole.USER and sample_buyer_email is None:
                sample_buyer_email = (role, email)
            elif role in [UserRole.VERIFIED_USER, UserRole.MODERATOR] and sample_host_email is None:
                sample_host_email = (role, email)

        if bulk_users:
            await self.execute_bulk(uow.user, bulk_users)

        self.print_raw_log("-" * 80)
        self.print_raw_log(
            f"{CLR_MAGENTA}[DEMO USERS PASSWORD] Shared Raw Password for this seed: {runtime_raw_password}{CLR_RESET}")
        self.print_raw_log("-" * 80)
        self.print_raw_log(f"{CLR_CYAN}{'ROLE':<18} | {'EMAIL':<30}{CLR_RESET}")
        self.print_raw_log("-" * 80)

        if sample_host_email:
            host_role, host_mail = sample_host_email
            self.print_raw_log(f"{host_role:<18} | {host_mail:<30}")
        if sample_buyer_email:
            buyer_role, buyer_mail = sample_buyer_email
            self.print_raw_log(f"{buyer_role:<18} | {buyer_mail:<30}")
        self.print_raw_log("-" * 80)

    async def _seed_categories(self, uow: SQLAlchemyUnitOfWork) -> None:
        existing_cats = await uow.event_category.all()
        cats_cache = {c.name: c for c in existing_cats}

        roots_to_create = [{"name": name, "parent_id": None} for name in CATEGORIES_POOL.keys() if
                           name not in cats_cache]
        if roots_to_create:
            created_roots = await self.execute_bulk(uow.event_category, roots_to_create)
            for r in created_roots:
                cats_cache[r.name] = r

        subs_to_create = []
        for root_name, subs in CATEGORIES_POOL.items():
            root_cat = cats_cache[root_name]
            for sub_name in subs:
                if sub_name not in cats_cache:
                    subs_to_create.append({"name": sub_name, "parent_id": root_cat.id})

        if subs_to_create:
            created_subs = await self.execute_bulk(uow.event_category, subs_to_create)
            for s in created_subs:
                cats_cache[s.name] = s

        for root_name, subs in CATEGORIES_POOL.items():
            for sub_name in subs:
                sub_cat = cats_cache.get(sub_name)
                if sub_cat:
                    self.leaf_category_ids.append(sub_cat.id)

    async def _seed_events(self, uow: SQLAlchemyUnitOfWork, count: int) -> None:
        now_utc = datetime.now(timezone.utc)
        historical_limit = max(1, int(count * 0.2))
        bulk_events_data = []
        event_states_cache = []

        for i in range(1, count + 1):
            title = f"{random.choice(EVENT_ADJECTIVES)} {random.choice(EVENT_NOUNS)} {random.randint(2026, 2027)}"
            description = f"Приглашаем вас на мероприятие '{title}'. Проведи время незабываемо!"
            e_type = random.choice([EventFormat.OFFLINE, EventFormat.ONLINE])
            address = random.choice(CITIES_POOL) if e_type == EventFormat.OFFLINE else None

            if i <= historical_limit:
                started_at = now_utc - timedelta(days=random.randint(2, 45))
                state = EventState.APPROVED
            else:
                started_at = now_utc + timedelta(days=random.randint(10, 200))
                state = random.choice([EventState.APPROVED, EventState.DRAFT, EventState.ON_MODERATION])

            bulk_events_data.append({
                "title": title, "description": description, "user_id": random.choice(self.allowed_event_hosts),
                "category_id": random.choice(self.leaf_category_ids), "state": state, "format": e_type,
                "address": address, "started_at": started_at
            })
            event_states_cache.append(state)

        if not bulk_events_data:
            return

        created_events = await self.execute_bulk(uow.event, bulk_events_data)
        bulk_tickets_data = []

        for idx, event_dto in enumerate(created_events):
            self.all_event_ids.append(event_dto.id)
            available_ticket_names = random.sample(TICKET_NAMES_POOL, k=random.randint(1, 3))
            for t_idx, ticket_name in enumerate(available_ticket_names):
                bulk_tickets_data.append({
                    "event_id": event_dto.id, "name": ticket_name,
                    "price": PRICES_POOL[t_idx % len(PRICES_POOL)], "total_quantity": random.randint(40, 300)
                })

        if bulk_tickets_data:
            created_tickets = await self.execute_bulk(uow.ticket_category, bulk_tickets_data)
            ticket_cursor = 0
            for idx, event_dto in enumerate(created_events):
                state = event_states_cache[idx]
                tickets_count = len([t for t in bulk_tickets_data if t["event_id"] == event_dto.id])
                if state == EventState.APPROVED:
                    for _ in range(tickets_count):
                        self.purchasable_ticket_categories.append(created_tickets[ticket_cursor])
                        ticket_cursor += 1
                else:
                    ticket_cursor += tickets_count

    async def _seed_orders(self, uow: SQLAlchemyUnitOfWork, count: int) -> None:
        if not self.purchasable_ticket_categories:
            return

        bulk_orders_data = []
        order_meta_cache = []

        for o_idx in range(1, count + 1):
            is_anon_purchase = random.random() < 0.25
            if is_anon_purchase:
                buyer_user_id = None
                anonymous_email = f"guest_{random.randint(10000, 99999)}@example.com"
            else:
                buyer_user_id = random.choice(self.regular_buyers) if self.regular_buyers else random.choice(
                    self.all_user_ids)
                anonymous_email = None

            order_status = random.choice([OrderStatus.PAID, OrderStatus.PENDING, OrderStatus.CANCELLED])
            target_cat = random.choice(self.purchasable_ticket_categories)
            ticket_qty = random.randint(1, 3)

            bulk_orders_data.append({
                "user_id": buyer_user_id, "anonymous_email": anonymous_email, "status": order_status
            })
            order_meta_cache.append({"category_id": target_cat.id, "quantity": ticket_qty})

        if not bulk_orders_data:
            return

        created_orders = await self.execute_bulk(uow.order, bulk_orders_data)
        bulk_items_data = []
        for idx, order_dto in enumerate(created_orders):
            meta = order_meta_cache[idx]
            bulk_items_data.append({
                "order_id": order_dto.id, "category_id": meta["category_id"], "quantity": meta["quantity"]
            })

        if bulk_items_data:
            await self.execute_bulk(uow.order_item, bulk_items_data)

    async def _seed_view_logs(self, uow: SQLAlchemyUnitOfWork) -> None:
        event_model_name = uow.event.get_model_name()
        total_users = len(self.all_user_ids)
        bulk_views_data = []

        for event_id in self.all_event_ids:
            max_viewers = min(15, total_users)
            min_viewers = min(5, max_viewers) if max_viewers > 0 else 0

            if max_viewers > 0:
                viewers = random.sample(self.all_user_ids, k=random.randint(min_viewers, max_viewers))
            else:
                viewers = []

            for _ in viewers:
                bulk_views_data.append(
                    {
                        "object_type": event_model_name,
                        "object_id": event_id,
                        "visitor_hash": secrets.token_hex(16)
                    }
                )

        if bulk_views_data:
            await self.execute_bulk(
                uow.view_logs, bulk_views_data, on_conflict_do_nothing=True,
                index_elements=["object_type", "object_id", "visitor_hash"]
            )

    def _print_dashboard(self, users: int, events: int, orders: int) -> None:
        from src.cli.colors import CLR_BOLD, CLR_GREEN, CLR_RESET
        t_users = self._pipeline_durations.get("users", 0.0)
        t_cats = self._pipeline_durations.get("categories", 0.0)
        t_events = self._pipeline_durations.get("events", 0.0)
        t_orders = self._pipeline_durations.get("orders", 0.0)
        t_views = self._pipeline_durations.get("views", 0.0)

        t_clean_str = f"    Database Cleanup:   {self._pipeline_durations['clean']:.2f}s\n" if "clean" in self._pipeline_durations else ""

        dashboard = (
            f"\n{CLR_GREEN}{CLR_BOLD}  Database seeding completed successfully.{CLR_RESET}\n\n"
            f"  Pipeline Profiling Metrics:\n"
            f"{t_clean_str}"
            f"    Users Generation:   {t_users:.2f}s\n"
            f"    Categories Build:   {t_cats:.2f}s\n"
            f"    Events Blueprint:   {t_events:.2f}s\n"
            f"    Orders Workflow:    {t_orders:.2f}s\n"
            f"    Traffic Analytics:  {t_views:.2f}s\n\n"
            f"  Generated Objects Summary:\n"
            f"    Users Registered:  {users + 1:<4} (1 Admin, {len(self.all_user_ids) - len(self.regular_buyers) - 1} Hosts, {len(self.regular_buyers)} Buyers)\n"
            f"    Leaf Categories:   {len(self.leaf_category_ids):<4}\n"
            f"    Total Events:      {events:<4} ({int(events * 0.2)} Historical, {events - int(events * 0.2)} Upcoming/Draft)\n"
            f"    Ticket Categories: {len(self.purchasable_ticket_categories):<4} Active pools\n"
            f"    Customer Orders:   {orders:<4}\n"
        )
        self.print_raw_log(dashboard)
