from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AutomationJobType(str, Enum):
    SERVER_BACKUP = "server_backup"
    SCHEDULED_UPLOAD = "scheduled_upload"


@dataclass(slots=True)
class AutomationJob:
    name: str
    enabled: bool
    job_type: AutomationJobType
    schedule_minute: int
    schedule_hour: int
    schedule_weekdays: str
    profile_id: int | None
    remote_path: str | None
    source_local_dir: str | None
    upload_roll_mode: str
    upload_fixed_roll: int | None
    keep_last_n: int
    id: int | None = None
    last_run_at: str | None = None
    last_status: str | None = None
    last_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(slots=True)
class AutomationRun:
    id: int
    job_id: int
    started_at: str
    finished_at: str
    status: str
    message: str | None


@dataclass(slots=True)
class AutomationExecutionResult:
    status: str
    message: str
