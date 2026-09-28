from abc import ABC, abstractmethod
from typing import Any


class BaseGeneratedMixin(ABC):
    @classmethod
    @abstractmethod
    def with_params(cls, *args: Any, **kwargs: Any) -> type:
        pass

    @classmethod
    def _generate(cls, suffix: str, container_cls: type) -> type:
        class GeneratedMixin(container_cls):
            pass

        safe_suffix = suffix.replace("/", "_").replace(".", "_").replace(" ", "_")
        GeneratedMixin.__name__ = f"{cls.__name__}_{safe_suffix}"
        return GeneratedMixin
