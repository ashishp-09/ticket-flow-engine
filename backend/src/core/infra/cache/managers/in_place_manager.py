from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, List, Dict, Optional, Union
from src.core.infra.cache.managers.abstract import AbstractCacheManager


class InMemoryCacheManager(AbstractCacheManager):

    def __init__(self) -> None:
        self._storage: dict[str, Any] = {}
        self._hll_storage: dict[str, set[Any]] = {}

    async def get(self, key: Union[str, List[str]]) -> Union[Any, List[Any]]:
        if isinstance(key, list):
            return [self._storage.get(k) for k in key]
        return self._storage.get(key)

    async def set(self, key: Union[str, Dict[str, Any]], value: Any = None, ttl: Optional[int] = None) -> None:
        if isinstance(key, dict):
            self._storage.update(key)
            return
        self._storage[key] = value

    async def incr(
        self,
        key: Union[str, List[str]],
        ttl: Optional[int] = None,
        expire_keys: Optional[List[str]] = None
    ) -> Union[int, List[int]]:
        if isinstance(key, list):
            results = []
            for c_key in key:
                val = int(self._storage.get(c_key, 0)) + 1
                self._storage[c_key] = val
                results.append(val)
            return results

        val = int(self._storage.get(key, 0)) + 1
        self._storage[key] = val
        return val

    async def pfadd(self, key: Union[str, List[str]], value: Any) -> Union[int, List[int]]:
        if isinstance(key, list):
            results = []
            for k in key:
                if k not in self._hll_storage:
                    self._hll_storage[k] = set()
                str_value = str(value)
                if str_value in self._hll_storage[k]:
                    results.append(0)
                else:
                    self._hll_storage[k].add(str_value)
                    results.append(1)
            return results

        if key not in self._hll_storage:
            self._hll_storage[key] = set()
        str_value = str(value)
        if str_value in self._hll_storage[key]:
            return 0
        self._hll_storage[key].add(str_value)
        return 1

    async def pfcount(self, key: str) -> int:
        if key not in self._hll_storage:
            return 0
        return len(self._hll_storage[key])

    async def expire(self, key: str, ttl: int) -> bool:
        return key in self._storage or key in self._hll_storage

    @asynccontextmanager
    async def lock(self, key: str, timeout: float, blocking_timeout: float) -> AsyncIterator[None]:
        if self._storage.get(key) == "processing":
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Request is already being processed."
            )
        self._storage[key] = "processing"
        try:
            yield
        finally:
            self._storage.pop(key, None)

    async def delete(self, key: str) -> None:
        self._storage.pop(key, None)
        self._hll_storage.pop(key, None)

    async def clear(self) -> None:
        self._storage.clear()
        self._hll_storage.clear()
