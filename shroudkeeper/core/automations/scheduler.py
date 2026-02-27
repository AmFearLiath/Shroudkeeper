from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

from core.automations.models import AutomationJob
from storage.repositories import AutomationJobRepository


class AutomationScheduler(QObject):
    job_due = Signal(int)
    state_changed = Signal(bool)

    def __init__(self, repository: AutomationJobRepository, interval_ms: int = 30000) -> None:
        super().__init__()
        self._repository = repository
        self._timer = QTimer(self)
        self._timer.setInterval(max(1000, interval_ms))
        self._timer.timeout.connect(self.tick)
        self._last_minute_key: str | None = None
        self._last_run_keys: dict[int, str] = {}

    def start(self) -> None:
        if self._timer.isActive():
            return
        self._timer.start()
        self.state_changed.emit(True)
        self.tick()

    def stop(self) -> None:
        if not self._timer.isActive():
            return
        self._timer.stop()
        self.state_changed.emit(False)

    def is_running(self) -> bool:
        return self._timer.isActive()

    def tick(self) -> None:
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        if self._last_minute_key == minute_key:
            return

        self._last_minute_key = minute_key
        due_jobs = self.compute_due_jobs(now)
        for job in due_jobs:
            self._last_run_keys[job.id or 0] = minute_key
            if job.id is not None:
                self.job_due.emit(job.id)

    def compute_due_jobs(self, now: datetime) -> list[AutomationJob]:
        jobs = self._repository.list_jobs()
        return [job for job in jobs if self.should_run(job, now)]

    def should_run(self, job: AutomationJob, now: datetime) -> bool:
        if not job.enabled or job.id is None:
            return False

        if int(job.schedule_minute) != now.minute or int(job.schedule_hour) != now.hour:
            return False

        if not self._weekday_matches(job.schedule_weekdays, now.weekday()):
            return False

        minute_key = now.strftime("%Y%m%d%H%M")
        if job.last_run_at is not None:
            try:
                last_run = datetime.fromisoformat(job.last_run_at.replace("Z", "+00:00"))
                if last_run.strftime("%Y%m%d%H%M") == minute_key:
                    return False
            except ValueError:
                pass

        return self._last_run_keys.get(job.id) != minute_key

    def _weekday_matches(self, weekdays_value: str, weekday: int) -> bool:
        cleaned = weekdays_value.strip()
        if cleaned == "*":
            return True

        values = set()
        for part in cleaned.split(","):
            part_clean = part.strip()
            if part_clean == "":
                continue
            try:
                index = int(part_clean)
            except ValueError:
                continue
            if 0 <= index <= 6:
                values.add(index)

        if len(values) == 0:
            return False
        return weekday in values
