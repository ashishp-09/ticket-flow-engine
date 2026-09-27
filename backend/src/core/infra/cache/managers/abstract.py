from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, List, Dict, Optional, Union, overload
from contextlib import asynccontextmanager


class AbstractCacheManager(ABC):

    @overload
    @abstractmethod
    async def get(self, key: str) -> Any: ...

    @overload
    @abstractmethod
    async def get(self, key: List[str]) -> List[Any]: ...

    @abstractmethod
    async def get(self, key: Union[str, List[str]]) -> Union[Any, List[Any]]: pass

    @overload
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...

    @overload
    @abstractmethod
    async def set(self, key: Dict[str, Any], value: None = None, ttl: Optional[int] = None) -> None: ...

    @abstractmethod
    async def set(self, key: Union[str, Dict[str, Any]], value: Any = None, ttl: Optional[int] = None) -> None: pass

    @overload
    @abstractmethod
    async def incr(self, key: str, ttl: Optional[int] = None) -> int: ...

    @overload
    @abstractmethod
    async def incr(self, key: List[str], ttl: Optional[int] = None, expire_keys: Optional[List[str]] = None) -> List[int]: ...

    @abstractmethod
    async def incr(
        self,
        key: Union[str, List[str]],
        ttl: Optional[int] = None,
        expire_keys: Optional[List[str]] = None
    ) -> Union[int, List[int]]: pass

    @overload
    @abstractmethod
    async def pfadd(self, key: str, value: Any) -> int: ...

    @overload
    @abstractmethod
    async def pfadd(self, key: List[str], value: Any) -> List[int]: ...

    @abstractmethod
    async def pfadd(self, key: Union[str, List[str]], value: Any) -> Union[int, List[int]]: pass

    @abstractmethod
    async def pfcount(self, key: str) -> int: pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool: pass

    @abstractmethod
    @asynccontextmanager
    async def lock(self, key: str, timeout: float, blocking_timeout: float) -> AsyncIterator[None]: pass

    @abstractmethod
    async def delete(self, key: str) -> None: pass

    @abstractmethod
    async def clear(self) -> None: pass
