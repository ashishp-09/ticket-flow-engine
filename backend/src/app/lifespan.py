from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.database import db_factory
from src.core.infra.cache.factory import get_cache_manager
from src.core.infra.tasks.config import broker as taskiq_broker
from src.core.infra.transport.queue.factory import get_queue_producer


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    await taskiq_broker.startup()

    kafka_broker = get_queue_producer.get_broker()
    await kafka_broker.connect()

    cache_manager = get_cache_manager()
    if hasattr(cache_manager, "redis_client"):
        await cache_manager.redis_client.ping()

    yield

    await kafka_broker.close()
    await taskiq_broker.shutdown()

    factory = get_cache_manager
    if hasattr(factory, "close"):
        factory.close()

    engine = db_factory.get_engine()
    await engine.dispose()
