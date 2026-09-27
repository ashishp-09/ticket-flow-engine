from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from src.core.settings import get_settings


settings = get_settings()


class DatabaseSessionFactory:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None
        self._readonly_session_maker: async_sessionmaker[AsyncSession] | None = None

    def _init_if_needed(self) -> None:
        if self._engine is None:
            self._engine = create_async_engine(
                settings.db_url,
                echo=settings.sql_logs,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
            )
            self._session_maker = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            self._readonly_session_maker = async_sessionmaker(
                bind=self._engine.execution_options(isolation_level="AUTOCOMMIT"),
                class_=AsyncSession,
                expire_on_commit=False,
            )

    def get_engine(self) -> AsyncEngine:
        self._init_if_needed()
        return self._engine

    def get_session_maker(self) -> async_sessionmaker[AsyncSession]:
        self._init_if_needed()
        return self._session_maker

    def get_readonly_session_maker(self) -> async_sessionmaker[AsyncSession]:
        self._init_if_needed()
        return self._readonly_session_maker


db_factory = DatabaseSessionFactory()
