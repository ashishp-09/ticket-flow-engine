import logging
from functools import wraps
from typing import Any, Callable

from fastapi import Response
from starlette import status

from src.core.infra.cache.exceptions import CacheUnavailableError
from src.core.infra.cache.factory import get_cache_manager
from .utils import _extract_request, _prepare_cache_payload, _resolve_status_code, _restore_response, \
    _should_cache, get_idempotency_cache_key, \
    get_idempotency_key, \
    get_idempotency_lock_key, \
    serialize_to_json

logger = logging.getLogger(__name__)


def idempotent_endpoint(ttl: int = 3600):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(*args, **kwargs)
            if request is None:
                return await func(*args, **kwargs)

            idempotency_key = get_idempotency_key(request)
            if not idempotency_key:
                return await func(*args, **kwargs)

            cache_manager = get_cache_manager()
            cache_key = get_idempotency_cache_key(idempotency_key)
            lock_key = get_idempotency_lock_key(cache_key)

            try:
                cached_data = await cache_manager.get(cache_key)
                if cached_data:
                    return _restore_response(cached_data)

                async with cache_manager.lock(lock_key, timeout=10.0, blocking_timeout=0.1):
                    cached_data = await cache_manager.get(cache_key)
                    if cached_data:
                        return _restore_response(cached_data)

                    response = await func(*args, **kwargs)
                    status_code = _resolve_status_code(response, request, *args, **kwargs)

                    if _should_cache(status_code):
                        payload = _prepare_cache_payload(response, status_code)
                        await cache_manager.set(cache_key, payload, ttl=ttl)

                    return response

            except CacheUnavailableError as e:
                logger.error(f"Idempotency cache storage down: {e}", exc_info=True)
                return Response(
                    content=serialize_to_json({"detail": "Service temporarily overloaded"}),
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    headers={"Retry-After": "1"},
                    media_type="application/json"
                )
            except Exception as e:
                logger.error(f"Idempotency internal system failure: {e}", exc_info=True)
                return await func(*args, **kwargs)

        return wrapper

    return decorator
