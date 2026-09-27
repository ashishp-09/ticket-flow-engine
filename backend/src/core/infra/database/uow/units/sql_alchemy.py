import inspect
from typing import Any, get_type_hints, Self, Type

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infra.database.exceptions import DatabaseExceptionMapper
from src.core.infra.database.repositories import GenericRepository
from src.core.infra.database.uow.units.abstract import AbstractUnitOfWork


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    _CLASS_HINTS_CACHE: dict[Type, dict[str, Any]] = {}

    def __init__(self, db_factory, exception_mapper: DatabaseExceptionMapper):
        self._db_factory = db_factory
        self._exception_mapper = exception_mapper
        self._session: AsyncSession | None = None
        self._repositories: dict[str, Any] = {}
        self._depth = 0
        self._transaction_stack: list[Any] = []
        self._is_readonly = False

        cls = self.__class__
        if cls not in self._CLASS_HINTS_CACHE:
            self._CLASS_HINTS_CACHE[cls] = get_type_hints(cls)

        self._repo_classes = self._CLASS_HINTS_CACHE[cls]
        self._validate_annotations()

    def _validate_annotations(self) -> None:
        seen_repo_classes: set[Type] = set()
        for attr_name, attr_type in self._repo_classes.items():
            if attr_name.startswith('_'):
                continue
            if not inspect.isclass(attr_type):
                raise TypeError(
                    f"Invalid annotation in {self.__class__.__name__}.{attr_name}: "
                    f"The type hint must resolve to a clean class. "
                    f"Using Union, Optional, or '| None' is forbidden."
                )
            if attr_type is GenericRepository or not issubclass(attr_type, GenericRepository):
                raise TypeError(
                    f"Invalid annotation in {self.__class__.__name__}.{attr_name}: "
                    f"Class '{attr_type.__name__}' must strictly inherit from 'GenericRepository'."
                )
            if attr_type in seen_repo_classes:
                raise ValueError(
                    f"Invalid configuration in {self.__class__.__name__}: "
                    f"Repository class '{attr_type.__name__}' is already assigned to another attribute."
                )
            seen_repo_classes.add(attr_type)

    def as_readonly(self) -> Self:
        if self._session is not None and not self._is_readonly:
            raise RuntimeError("Cannot change mode after the session has started.")
        self._is_readonly = True
        return self

    async def __aenter__(self) -> Self:
        if self._session is None:
            if self._is_readonly:
                factory = self._db_factory.get_readonly_session_maker()
            else:
                factory = self._db_factory.get_session_maker()
            self._session = factory()

        self._depth += 1
        if self._depth > 1 and not self._is_readonly:
            savepoint = await self._session.begin_nested()
            self._transaction_stack.append(savepoint)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._depth -= 1
        if self._depth > 0:
            if not self._is_readonly:
                savepoint = self._transaction_stack.pop()
                if exc_type is not None:
                    await savepoint.rollback()
                else:
                    await savepoint.commit()
            return

        if self._session:
            try:
                if exc_type is not None and not self._is_readonly:
                    await self._session.rollback()
            finally:
                await self._session.close()
                self._session = None
                self._repositories.clear()
                self._is_readonly = False

    def __getattr__(self, name: str) -> Any:
        if name in self._repositories:
            return self._repositories[name]

        if name not in self._repo_classes:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        repo_cls = self._repo_classes[name]

        if self._session is None:
            return repo_cls

        repo_instance = repo_cls(self._session, self._exception_mapper)
        self._repositories[name] = repo_instance
        return repo_instance

    def get_repo_cls(self, repo_name: str) -> Type[GenericRepository]:
        if repo_name not in self._repo_classes:
            raise AttributeError(f"'{self.__class__.__name__}' has no registered repository named '{repo_name}'")
        return self._repo_classes[repo_name]

    async def commit(self) -> None:
        if self._is_readonly:
            raise RuntimeError("Commit is forbidden in read_only mode.")
        if self._session:
            await self._session.commit()

    async def flush(self, *args: Any, **kwargs: Any) -> None:
        if self._session:
            await self._session.flush(*args, **kwargs)
