import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from src.app.uow import create_app_uow
from src.cli.colors import CLR_RESET, CLR_GREEN, CLR_CYAN, CLR_YELLOW, CLR_RED, CLR_BOLD, CLR_GRAY
from src.cli.enums import StepStatus
from src.core.infra.database.repositories import GenericRepository
from src.core.infra.database.uow.units import SQLAlchemyUnitOfWork


class BaseCommand(ABC):
    name: str
    description: str

    def __init__(self) -> None:
        self._pipeline_keys: list[str] = []
        self._pipeline_labels: dict[str, str] = {}
        self._pipeline_statuses: dict[str, StepStatus] = {}
        self._pipeline_timers: dict[str, float] = {}
        self._pipeline_durations: dict[str, float] = {}
        self._current_sub_log: str = ""
        self._active_step_key: str | None = None
        self._lines_printed_last_time: int = 0

    def set_pipeline(self, steps: list[tuple[str, str]]) -> None:
        self._pipeline_keys = [k for k, _ in steps]
        self._pipeline_labels = {k: l for k, l in steps}
        self._pipeline_statuses = {k: StepStatus.PENDING for k, _ in steps}
        self._pipeline_timers = {}
        self._pipeline_durations = {}
        self._current_sub_log = ""
        self._active_step_key = None
        self._lines_printed_last_time = 0
        self._render_pipeline()

    def start_step(self, key: str) -> None:
        if self._active_step_key:
            self._finish_step(self._active_step_key, StepStatus.SUCCESS)
        self._active_step_key = key
        self._pipeline_statuses[key] = StepStatus.RUNNING
        self._pipeline_timers[key] = time.time()
        self._current_sub_log = ""
        self._render_pipeline()

    def update_sub(self, message: str) -> None:
        self._current_sub_log = message
        self._render_pipeline()

    def _finish_step(self, key: str, status: StepStatus) -> None:
        self._pipeline_statuses[key] = status
        if key in self._pipeline_timers:
            self._pipeline_durations[key] = time.time() - self._pipeline_timers[key]
        self._current_sub_log = ""

    def _clear_last_render(self) -> None:
        if self._lines_printed_last_time > 0:
            for _ in range(self._lines_printed_last_time):
                sys.stdout.write("\033[F\033[K")
            self._lines_printed_last_time = 0

    def _render_pipeline(self) -> None:
        self._clear_last_render()
        lines = []

        if any(s == StepStatus.FAILED for s in self._pipeline_statuses.values()):
            lines.append(f"{CLR_RED}{CLR_BOLD}[ CRITICAL ] Command '{self.name}' failed!{CLR_RESET}")
        elif all(s == StepStatus.SUCCESS for s in self._pipeline_statuses.values()) and not self._active_step_key:
            lines.append(f"{CLR_GREEN}{CLR_BOLD}[ 100% ] Command '{self.name}' finished successfully!{CLR_RESET}")
        else:
            lines.append(f"{CLR_YELLOW}[ RUNNING ] Command '{self.name}' is in progress...{CLR_RESET}")

        for key in self._pipeline_keys:
            status = self._pipeline_statuses[key]
            label = self._pipeline_labels[key]

            if status == StepStatus.PENDING:
                lines.append(f"  {CLR_GRAY}● {label}{CLR_RESET}")
            elif status == StepStatus.RUNNING:
                elapsed = time.time() - self._pipeline_timers.get(key, time.time())
                lines.append(f"  {CLR_YELLOW}→ {label}{CLR_RESET} {CLR_GRAY}({elapsed:.1f}s){CLR_RESET}")
                if self._current_sub_log:
                    lines.append(f"    {CLR_GRAY}↳ {self._current_sub_log}{CLR_RESET}")
            elif status == StepStatus.SUCCESS:
                duration = self._pipeline_durations.get(key, 0.0)
                lines.append(f"  {CLR_GREEN}✔ {label}{CLR_RESET} {CLR_GRAY}({duration:.1f}s){CLR_RESET}")
            elif status == StepStatus.FAILED:
                duration = self._pipeline_durations.get(key, 0.0)
                lines.append(f"  {CLR_RED}✖ {label}{CLR_RESET} {CLR_GRAY}({duration:.1f}s){CLR_RESET}")

        for line in lines:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
        self._lines_printed_last_time = len(lines)

    def print_raw_log(self, text: str) -> None:
        self._clear_last_render()
        print(text)
        self._render_pipeline()

    def parse_args(self, args: list[str]) -> dict:
        return {}

    @abstractmethod
    async def handle(self, uow: SQLAlchemyUnitOfWork, **options) -> None:
        pass

    async def execute(self, args: list[str]) -> None:
        print(f"{CLR_CYAN}[ START ] Running command: {self.name}...{CLR_RESET}")
        start_time = datetime.now(timezone.utc)

        try:
            kwargs = self.parse_args(args)
        except ValueError as e:
            print(f"{CLR_RED}Argument parsing error: {e}{CLR_RESET}")
            return

        uow = create_app_uow()

        try:
            async with uow:
                await self.handle(uow, **kwargs)
                if self._active_step_key:
                    self._finish_step(self._active_step_key, StepStatus.SUCCESS)
                self._render_pipeline()
                await uow.commit()

            self._clear_last_render()
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(
                f"{CLR_GREEN}{CLR_BOLD}[ 100% ] {self.name} completed successfully in {duration:.2f} seconds.{CLR_RESET}")
        except Exception as e:
            if self._active_step_key:
                self._finish_step(self._active_step_key, StepStatus.FAILED)
            self._render_pipeline()
            print(f"\n{CLR_RED}{CLR_BOLD}[ CRITICAL ] Command '{self.name}' failed with exception: {e}{CLR_RESET}")
            raise e

    async def execute_bulk(self, repo: GenericRepository, m_data: list[dict], **kwargs) -> list:
        if not m_data:
            return []

        inserted_dtos = []
        total_items = len(m_data)
        table_name = repo.get_model_name()

        fields_count = len(m_data[0]) if m_data else 1
        chunk_size = max(100, 30000 // fields_count)

        for i in range(0, total_items, chunk_size):
            chunk = m_data[i:i + chunk_size]
            current_end = min(i + chunk_size, total_items)

            self.update_sub(f"Batch writing {table_name}: {current_end} / {total_items}...")

            res = await repo.create(m_data=chunk, **kwargs)
            if res:
                if isinstance(res, list):
                    inserted_dtos.extend(res)
                else:
                    inserted_dtos.append(res)

        return inserted_dtos


