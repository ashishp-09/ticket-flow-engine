import logging

from src.core.settings import get_settings
from src.core.infra.tasks.config import broker, scheduler
from src.core.infra.tasks.managers import TaskIqTaskManager


logger = logging.getLogger("taskiq")


class TaskManagerFactory:
    def __init__(self):
        self._instance: TaskIqTaskManager | None = None

    def __call__(self) -> TaskIqTaskManager:
        if self._instance is None:
            settings = get_settings()

            schedule_source = None if settings.testing else scheduler.sources[0]

            self._instance = TaskIqTaskManager(
                broker=broker,
                schedule_source=schedule_source
            )

        return self._instance


get_task_manager = TaskManagerFactory()
