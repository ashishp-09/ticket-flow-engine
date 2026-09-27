import hashlib
import logging
from collections import Counter
from typing import Any, overload, Union

from src.core.infra.cache.exceptions import CacheUnavailableError
from .data_objects import VisitorData
from .protocols import ViewableServiceProtocol

logger = logging.getLogger(__name__)


class ViewableServiceMixin:
    def _get_visitor_hash(self, visitor_data: VisitorData) -> str:
        raw_fingerprint = f"{visitor_data.ip_address}:{visitor_data.user_agent}"
        return hashlib.md5(raw_fingerprint.encode("utf-8")).hexdigest()

    def _get_model_name(self) -> str:
        raise NotImplementedError(
            f"Service '{self.__class__.__name__}' uses ViewableServiceMixin "
            f"but does not implement the '_get_model_name()' method."
        )

    def _get_cache_key(self: ViewableServiceProtocol, obj_id: int) -> str:
        return f"views:{self._get_model_name()}:{obj_id}"

    def _get_hll_key(self: ViewableServiceProtocol, obj_id: int) -> str:
        return f"views:{self._get_model_name()}:{obj_id}:daily_hll"

    @overload
    async def get_views(self: ViewableServiceProtocol, obj_id: int) -> int:
        ...

    @overload
    async def get_views(self: ViewableServiceProtocol, obj_id: list[int]) -> dict[int, int]:
        ...

    async def get_views(self: ViewableServiceProtocol, obj_id: Union[int, list[int]]) -> Union[int, dict[int, int]]:
        if isinstance(obj_id, list):
            if not obj_id:
                return {}

            id_to_key = {oid: self._get_cache_key(oid) for oid in obj_id}
            keys = list(id_to_key.values())

            cached_values = None
            try:
                cached_values = await self.cache.get(keys)
            except CacheUnavailableError as e:
                logger.warning(f"Cache down in get_views (batch) for {self._get_model_name()}: {e}")

            final_counts, missing_ids = {}, []
            if cached_values:
                for (oid, key), val in zip(id_to_key.items(), cached_values):
                    if val is not None:
                        final_counts[oid] = int(val)
                    else:
                        missing_ids.append(oid)
            else:
                missing_ids = list(obj_id)

            if missing_ids:
                async with self.uow.as_readonly():
                    logs = await (
                        self.uow.view_logs
                        .filter(
                            object_type=self._get_model_name(),
                            object_id__in=missing_ids
                        )
                        .all()
                    )

                counts_map = Counter(log.object_id for log in logs)
                db_results = {oid: counts_map[oid] for oid in missing_ids}
                final_counts.update(db_results)

                if cached_values is not None:
                    try:
                        cache_mapping = {id_to_key[m_id]: db_results[m_id] for m_id in missing_ids}
                        await self.cache.set(cache_mapping, ttl=86400)
                    except CacheUnavailableError as e:
                        logger.warning(f"Failed to fill cache in get_views (batch) for {self._get_model_name()}: {e}")

            return final_counts

        cache_key = self._get_cache_key(obj_id)
        lock_key = f"lock:{cache_key}"

        try:
            cached_views = await self.cache.get(cache_key)
            if cached_views is not None:
                return int(cached_views)
        except CacheUnavailableError as e:
            logger.warning(f"Cache down in get_views (single) for {self._get_model_name()}: {e}")
            cached_views = None

        if cached_views is None:
            try:
                async with self.cache.lock(lock_key, timeout=5.0, blocking_timeout=3.0):
                    cached_views = await self.cache.get(cache_key)
                    if cached_views is not None:
                        return int(cached_views)

                    async with self.uow.as_readonly():
                        db_count = await (
                            self.uow.view_logs
                            .filter(
                                object_type=self._get_model_name(),
                                object_id=obj_id
                            )
                            .count()
                        )

                    await self.cache.set(cache_key, db_count, ttl=86400)
                    return db_count
            except CacheUnavailableError as e:
                logger.warning(
                    f"Cache lock/operations down in get_views for {self._get_model_name()}, using direct DB query: {e}")
                async with self.uow.as_readonly():
                    return await (
                        self.uow.view_logs
                        .filter(
                            object_type=self._get_model_name(),
                            object_id=obj_id
                        )
                        .count()
                    )

    @overload
    async def increment_views(self: ViewableServiceProtocol, obj_id: int, visitor_data: VisitorData) -> None:
        ...

    @overload
    async def increment_views(self: ViewableServiceProtocol, obj_id: list[int], visitor_data: VisitorData) -> None:
        ...

    async def increment_views(
            self: ViewableServiceProtocol,
            obj_id: Union[int, list[int]],
            visitor_data: VisitorData
    ) -> None:
        if not visitor_data or not obj_id:
            return

        visitor_hash = self._get_visitor_hash(visitor_data)

        if isinstance(obj_id, list):
            try:
                hll_keys = [self._get_hll_key(oid) for oid in obj_id]
                uniques_mask = await self.cache.pfadd(hll_keys, visitor_hash)
                unique_ids = [oid for oid, is_unique in zip(obj_id, uniques_mask) if is_unique]

                if not unique_ids:
                    return

                target_cache_keys = [self._get_cache_key(oid) for oid in unique_ids]
                target_hll_keys = [self._get_hll_key(oid) for oid in unique_ids]
                await self.cache.incr(target_cache_keys, ttl=86400, expire_keys=target_hll_keys)
            except CacheUnavailableError as e:
                logger.warning(f"Cache storage down during increment_views (batch) for {self._get_model_name()}: {e}")
                unique_ids = list(obj_id)

            await self.queue.send(
                destination="view_logs_queue",
                payload={
                    "object_type": self._get_model_name(),
                    "object_ids": unique_ids,
                    "visitor_hash": visitor_hash
                }
            )
            return

        try:
            hll_key = self._get_hll_key(obj_id)
            is_new_view = await self.cache.pfadd(hll_key, visitor_hash)
            if is_new_view:
                cache_key = self._get_cache_key(obj_id)
                await self.cache.incr(cache_key)
                await self.cache.expire(hll_key, 86400)
        except CacheUnavailableError as e:
            logger.warning(f"Cache storage down during increment_views (single) for {self._get_model_name()}: {e}")
            is_new_view = True

        if is_new_view:
            await self.queue.send(
                destination="view_logs_queue",
                payload={
                    "object_type": self._get_model_name(),
                    "object_ids": [obj_id],
                    "visitor_hash": visitor_hash
                }
            )



    @overload
    async def _enrich_with_views(self: ViewableServiceProtocol, items: Any) -> Any:
        ...

    @overload
    async def _enrich_with_views(self: ViewableServiceProtocol, items: list[Any]) -> list[Any]:
        ...

    async def _enrich_with_views(self: ViewableServiceProtocol, items: Any | list[Any]) -> Any | list[Any]:
        if not items:
            return items

        if isinstance(items, list):
            ids = [e.id for e in items]
            views_map = await self.get_views(obj_id=ids)
            for item in items:
                item.views = views_map.get(item.id, 0)
            return items

        items.views = await self.get_views(obj_id=items.id)
        return items
