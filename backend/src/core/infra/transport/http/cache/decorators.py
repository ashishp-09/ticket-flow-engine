import logging
import time
from functools import wraps
from typing import Any, Callable, List, Union

from fastapi import Request, Response

from src.app.exceptions import ServiceException
from src.core.infra.cache.exceptions import CacheUnavailableError
from src.core.infra.cache.factory import get_cache_manager
from .utils import (
    generate_query_hash,
    get_composite_cache_key,
    get_version_key,
    serialize_to_json,
)

logger = logging.getLogger(__name__)


def cached_endpoint(tags: Union[str, List[str]], ttl: int = 3600):
    tag_list = [tags] if isinstance(tags, str) else list(tags)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request = kwargs.get("request") or next(
                (arg for arg in args if isinstance(arg, Request)), None
            )
            if request is None:
                return await func(*args, **kwargs)

            cache_manager = get_cache_manager()
            query_hash = generate_query_hash(request)

            try:
                version_keys = [get_version_key(t) for t in tag_list]
                raw_versions = await cache_manager.get(version_keys)
                tags_versions = {}
                missing_tags_to_set = {}

                for idx, tag_name in enumerate(tag_list):
                    version = raw_versions[idx] if raw_versions and idx < len(raw_versions) else None
                    if not version:
                        version = str(int(time.time() * 1000))
                        missing_tags_to_set[get_version_key(tag_name)] = version
                    tags_versions[tag_name] = version

                if missing_tags_to_set:
                    await cache_manager.set(missing_tags_to_set, ttl=ttl * 2)

                cache_key = get_composite_cache_key(tag_list, tags_versions, query_hash)
                cached_data = await cache_manager.get(cache_key)
                if cached_data:
                    return Response(content=cached_data, media_type="application/json")

                response = await func(*args, **kwargs)
                json_str = serialize_to_json(response)
                await cache_manager.set(cache_key, json_str, ttl=ttl)
                return response

            except ServiceException:
                raise
            except CacheUnavailableError as e:
                logger.warning(f"Cache storage unavailable for tags {tag_list}, bypassing to DB: {e}")
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Cache system failure for tags {tag_list}: {e}", exc_info=True)
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def invalidates_cache(tags: Union[str, List[str]]):
    tag_list = [tags] if isinstance(tags, str) else list(tags)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            response = await func(*args, **kwargs)
            try:
                cache_manager = get_cache_manager()
                new_version = str(int(time.time() * 1000))
                version_updates = {get_version_key(t): new_version for t in tag_list}
                await cache_manager.set(version_updates)
            except CacheUnavailableError as e:
                logger.error(f"Failed to invalidate cache tags due to storage unavailability {tag_list}: {e}")
            except Exception as e:
                logger.error(f"Failed to invalidate cache tags {tag_list}: {e}", exc_info=True)
            return response

        return wrapper

    return decorator
