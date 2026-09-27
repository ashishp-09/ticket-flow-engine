from abc import ABC, abstractmethod
from typing import Any


class AbstractTaskManager(ABC):
    @abstractmethod
    async def perform_task(
        self,
        name: str,
        *,
        delay: int | None = None,
        queue: str | None = None,
        priority: str | None = None,
        **task_kwargs: Any,
    ) -> str:
        pass
