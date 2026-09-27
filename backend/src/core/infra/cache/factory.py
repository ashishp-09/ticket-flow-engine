from redis.asyncio import ConnectionPool, Redis

from src.core.infra.cache.managers import AbstractCacheManager, InMemoryCacheManager, RedisCacheManager
from src.core.settings import get_settings


class CacheManagerFactory:
    def __init__(self):
        self._instance: AbstractCacheManager | None = None
        self._pool: ConnectionPool | None = None

    def __call__(self) -> AbstractCacheManager:
        if self._instance is None:
            settings = get_settings()
            if settings.testing:
                self._instance = InMemoryCacheManager()
            else:
                self._pool = ConnectionPool.from_url(
                    url=settings.redis_url,
                    max_connections=settings.redis_pool_size,
                    socket_timeout=2.0,
                    socket_connect_timeout=1.0,
                    health_check_interval=30
                )
                client = Redis(connection_pool=self._pool)
                self._instance = RedisCacheManager(redis_client=client)
        return self._instance

    def close(self) -> None:
        if self._pool is not None:
            self._pool.disconnect()


get_cache_manager = CacheManagerFactory()
