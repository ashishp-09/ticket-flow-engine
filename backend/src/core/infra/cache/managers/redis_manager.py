from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from redis.asyncio import Redis
from redis.exceptions import LockError, RedisError

from src.core.infra.cache.exceptions import CacheUnavailableError
from src.core.infra.cache.managers.abstract import AbstractCacheManager


class RedisCacheManager(AbstractCacheManager):
    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    @property
    def redis_client(self) -> Redis:
        return self._redis

    async def get(self, key: Union[str, List[str]]) -> Union[Any, List[Any]]:
        try:
            if isinstance(key, list):
                if not key:
                    return []
                return await self._redis.mget(key)
            return await self._redis.get(key)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def set(self, key: Union[str, Dict[str, Any]], value: Any = None, ttl: Optional[int] = None) -> None:
        try:
            if isinstance(key, dict):
                if not key:
                    return
                async with self._redis.pipeline(transaction=False) as pipe:
                    for k, v in key.items():
                        pipe.set(k, v, ex=ttl)
                    await pipe.execute()
                return
            await self._redis.set(key, value, ex=ttl)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def incr(
            self,
            key: Union[str, List[str]],
            ttl: Optional[int] = None,
            expire_keys: Optional[List[str]] = None
    ) -> Union[int, List[int]]:
        try:
            if isinstance(key, list):
                if not key:
                    return []
                async with self._redis.pipeline(transaction=False) as pipe:
                    for c_key in key:
                        pipe.incr(c_key)
                    if expire_keys and ttl is not None:
                        for h_key in expire_keys:
                            pipe.expire(h_key, ttl)
                    results = await pipe.execute()
                    return [res for res in results if isinstance(res, int)]

            val = await self._redis.incr(key)
            if ttl is not None:
                await self._redis.expire(key, ttl)
            return val
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def pfadd(self, key: Union[str, List[str]], value: Any) -> Union[int, List[int]]:
        try:
            if isinstance(key, list):
                if not key:
                    return []
                async with self._redis.pipeline(transaction=False) as pipe:
                    for k in key:
                        pipe.pfadd(k, value)
                    return await pipe.execute()
            return await self._redis.pfadd(key, value)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def pfcount(self, key: str) -> int:
        try:
            return await self._redis.pfcount(key)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def expire(self, key: str, ttl: int) -> bool:
        try:
            return await self._redis.expire(key, ttl)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    @asynccontextmanager
    async def lock(self, key: str, timeout: float, blocking_timeout: float) -> AsyncIterator[None]:
        redis_lock = None
        try:
            redis_lock = self._redis.lock(key, timeout=timeout, blocking_timeout=blocking_timeout)
            acquired = await redis_lock.acquire()
            if not acquired:
                raise TimeoutError(f"Failed to obtain lock {key} within {blocking_timeout} seconds.")
            yield
        except LockError as e:
            raise CacheUnavailableError(str(e)) from e
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e
        finally:
            if redis_lock is not None:
                try:
                    await redis_lock.release()
                except LockError:
                    pass

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e

    async def clear(self) -> None:
        try:
            await self._redis.flushdb()
        except RedisError as e:
            raise CacheUnavailableError(str(e)) from e
