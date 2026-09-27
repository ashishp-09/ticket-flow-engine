from typing import Any

from src.app.uow import AppUnitOfWork
from src.domain.services import GenericService


class ViewLogService(GenericService[AppUnitOfWork]):
    async def process_view_logs(
            self,
            payloads: list[dict[str, Any]]
    ) -> int:
        flat_logs = []
        for payload in payloads:
            object_type = payload["object_type"]
            visitor_hash = payload["visitor_hash"]
            for oid in payload["object_ids"]:
                flat_logs.append({
                    "object_type": object_type,
                    "object_id": oid,
                    "visitor_hash": visitor_hash
                })

        if not flat_logs:
            return 0

        async with self.uow:
            processed = await self.uow.view_logs.create(
                flat_logs,
                on_conflict_do_nothing=True,
                index_elements=["object_type", "object_id", "visitor_hash"],
                returning=False
            )
            await self.uow.commit()

        return processed
