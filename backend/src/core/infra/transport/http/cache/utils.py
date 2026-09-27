import asyncio
import hashlib
import random
from typing import Any, List, Dict
from fastapi import Request
import orjson


def generate_query_hash(request: Request) -> str:
    url_path = request.url.path
    sorted_params = sorted(request.query_params.items())
    params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
    raw_query_key = f"{url_path}?{params_str}"
    return hashlib.md5(raw_query_key.encode("utf-8")).hexdigest()


def _orjson_default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    raise TypeError(f"Type {type(obj)} not serializable by orjson")


def serialize_to_json(data: Any) -> str:
    return orjson.dumps(data, default=_orjson_default).decode("utf-8")


def get_version_key(tag: str) -> str:
    return f"{tag}:version"


def get_lock_key(main_tag: str, query_hash: str) -> str:
    return f"lock:{main_tag}:{query_hash}"


def get_composite_cache_key(tags: List[str], tags_versions: Dict[str, str], query_hash: str) -> str:
    sorted_tags = sorted(tags)
    version_part = "_".join(f"{tag_name}:{tags_versions[tag_name]}" for tag_name in sorted_tags)
    return f"cache:{version_part}:{query_hash}"


async def wait_for_cached_data(
        cache_manager: Any,
        version_keys: List[str],
        tag_list: List[str],
        query_hash: str,
        max_attempts: int = 3,
        initial_delay: float = 0.03
) -> Any:
    delay = initial_delay

    jitter = random.uniform(0.005, 0.015)
    await asyncio.sleep(jitter)

    for _ in range(max_attempts):
        current_raw_versions = await cache_manager.get(version_keys)

        current_tags_versions = {}
        for idx, tag_name in enumerate(tag_list):
            current_tags_versions[tag_name] = (
                current_raw_versions[idx] if idx < len(current_raw_versions) else "default"
            )

        current_cache_key = get_composite_cache_key(tag_list, current_tags_versions, query_hash)

        cached_data = await cache_manager.get(current_cache_key)
        if cached_data:
            return cached_data

        await asyncio.sleep(delay)
        delay *= 1.5

    return None

