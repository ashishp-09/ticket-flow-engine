from datetime import datetime, timedelta, timezone
from typing import Any

from taskiq import AsyncBroker, ScheduledTask, ScheduleSource
from taskiq.kicker import AsyncKicker

from src.core.infra.tasks.managers.abstract import AbstractTaskManager


class TaskIqTaskManager(AbstractTaskManager):
    def __init__(self, broker: AsyncBroker, schedule_source: ScheduleSource | None = None) -> None:
        self._broker = broker
        self._schedule_source = schedule_source

    def _build_labels(self, queue: str | None, priority: str | None) -> dict[str, Any]:
        labels: dict[str, Any] = {}
        if queue:
            labels["queue"] = queue
        if priority:
            labels["priority"] = priority
        return labels

    async def perform_task(
        self,
        name: str,
        *,
        delay: int | None = None,
        queue: str | None = None,
        priority: str | None = None,
        **task_kwargs: Any,
    ) -> str:
        labels = self._build_labels(queue, priority)

        if delay is not None and self._schedule_source is not None:
            generated_id = f"delayed:{name}:{datetime.now(timezone.utc).timestamp()}"
            labels["_taskiq_schedule_once"] = True

            scheduled_task = ScheduledTask(
                task_name=name,
                labels=labels,
                args=[],
                kwargs=task_kwargs,
                time=datetime.now(timezone.utc) + timedelta(seconds=delay),
            )

            scheduled_task.schedule_id = generated_id

            await self._schedule_source.add_schedule(scheduled_task)
            return generated_id

        kicker = AsyncKicker(
            task_name=name,
            broker=self._broker,
            labels=labels,
        )

        task_info = await kicker.kiq(**task_kwargs)
        return task_info.task_id
