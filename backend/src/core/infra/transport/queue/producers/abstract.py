from abc import ABC, abstractmethod
from typing import Any


class AbstractQueueProducer(ABC):
    @abstractmethod
    async def send(self, destination: str, payload: dict[str, Any]) -> None: ...
