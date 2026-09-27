from abc import ABC, abstractmethod
from typing import Any, Sequence


class BaseQueryModifier(ABC):
    @abstractmethod
    def apply_to_query(self, query: Any, current_model: Any) -> Any:
        pass

    @abstractmethod
    def process_results(self, rows: Sequence[Any], current_model: Any) -> None:
        pass
