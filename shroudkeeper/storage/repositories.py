from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3

from core.automations.models import AutomationJob, AutomationJobType, AutomationRun
from core.profiles.models import Profile


@dataclass(slots=True)
class Job:
    id: int
    profile_id: int
    name: str
    direction: str
    enabled: int
    cron_expression: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class JobRun:
    id: int
    job_id: int
    started_at: str
    finished_at: str | None
    status: str
    message: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("Insert did not return a row id")
    return int(cursor.lastrowid)


class ProfileRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_profiles(self) -> list[Profile]:
        rows = self._connection.execute(
            """
            SELECT
                id,
                name,
                protocol,
                host,
                port,
                username,
                remote_path,
                passive_mode,
                verify_host_key,
                created_at,
                updated_at
            FROM profiles
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def get_profile(self, profile_id: int) -> Profile | None:
        row = self._connection.execute(
            """
            SELECT
                id,
                name,
                protocol,
                host,
                port,
                username,
                remote_path,
                passive_mode,
                verify_host_key,
                created_at,
                updated_at
            FROM profiles
            WHERE id = ?
            """,
            (profile_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def create_profile(self, profile: Profile) -> int:
        now = _utc_now_iso()
        cursor = self._connection.execute(
            """
            INSERT INTO profiles (
                name,
                protocol,
                host,
                port,
                username,
                remote_path,
                passive_mode,
                verify_host_key,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.name,
                profile.protocol,
                profile.host,
                profile.port,
                profile.username,
                profile.remote_path,
                1 if profile.passive_mode else 0,
                1 if profile.verify_host_key else 0,
                now,
                now,
            ),
        )
        self._connection.commit()
        return _require_lastrowid(cursor)

    def update_profile(self, profile: Profile) -> None:
        if profile.id is None:
            raise ValueError("profile.id is required for update")

        now = _utc_now_iso()
        self._connection.execute(
            """
            UPDATE profiles
            SET
                name = ?,
                protocol = ?,
                host = ?,
                port = ?,
                username = ?,
                remote_path = ?,
                passive_mode = ?,
                verify_host_key = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                profile.name,
                profile.protocol,
                profile.host,
                profile.port,
                profile.username,
                profile.remote_path,
                1 if profile.passive_mode else 0,
                1 if profile.verify_host_key else 0,
                now,
                profile.id,
            ),
        )
        self._connection.commit()

    def delete_profile(self, profile_id: int) -> None:
        self._connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        self._connection.commit()

    def _row_to_profile(self, row: sqlite3.Row) -> Profile:
        return Profile(
            id=int(row["id"]),
            name=str(row["name"]),
            protocol=str(row["protocol"]),
            host=str(row["host"]),
            port=int(row["port"]),
            username=str(row["username"]),
            remote_path=str(row["remote_path"]),
            passive_mode=bool(row["passive_mode"]),
            verify_host_key=bool(row["verify_host_key"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


class JobRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(
        self,
        profile_id: int,
        name: str,
        direction: str,
        enabled: int = 1,
        cron_expression: str | None = None,
    ) -> int:
        now = _utc_now_iso()
        cursor = self._connection.execute(
            """
            INSERT INTO jobs (profile_id, name, direction, enabled, cron_expression, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (profile_id, name, direction, enabled, cron_expression, now, now),
        )
        self._connection.commit()
        return _require_lastrowid(cursor)

    def list_by_profile(self, profile_id: int) -> list[Job]:
        rows = self._connection.execute(
            """
            SELECT id, profile_id, name, direction, enabled, cron_expression, created_at, updated_at
            FROM jobs
            WHERE profile_id = ?
            ORDER BY name
            """,
            (profile_id,),
        ).fetchall()
        return [Job(**dict(row)) for row in rows]


class JobRunRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, job_id: int, status: str, message: str | None = None) -> int:
        started_at = _utc_now_iso()
        cursor = self._connection.execute(
            """
            INSERT INTO job_runs (job_id, started_at, status, message)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, started_at, status, message),
        )
        self._connection.commit()
        return _require_lastrowid(cursor)

    def finish(self, run_id: int, status: str, message: str | None = None) -> None:
        finished_at = _utc_now_iso()
        self._connection.execute(
            """
            UPDATE job_runs
            SET finished_at = ?, status = ?, message = ?
            WHERE id = ?
            """,
            (finished_at, status, message, run_id),
        )
        self._connection.commit()

    def list_for_job(self, job_id: int) -> list[JobRun]:
        rows = self._connection.execute(
            """
            SELECT id, job_id, started_at, finished_at, status, message
            FROM job_runs
            WHERE job_id = ?
            ORDER BY started_at DESC
            """,
            (job_id,),
        ).fetchall()
        return [JobRun(**dict(row)) for row in rows]


class AutomationJobRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def list_jobs(self) -> list[AutomationJob]:
        rows = self._connection.execute(
            """
            SELECT
                id,
                name,
                enabled,
                job_type,
                schedule_minute,
                schedule_hour,
                schedule_weekdays,
                profile_id,
                remote_path,
                source_local_dir,
                upload_roll_mode,
                upload_fixed_roll,
                keep_last_n,
                last_run_at,
                last_status,
                last_message,
                created_at,
                updated_at
            FROM automation_jobs
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_job(self, job_id: int) -> AutomationJob | None:
        row = self._connection.execute(
            """
            SELECT
                id,
                name,
                enabled,
                job_type,
                schedule_minute,
                schedule_hour,
                schedule_weekdays,
                profile_id,
                remote_path,
                source_local_dir,
                upload_roll_mode,
                upload_fixed_roll,
                keep_last_n,
                last_run_at,
                last_status,
                last_message,
                created_at,
                updated_at
            FROM automation_jobs
            WHERE id = ?
            """,
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def create_job(self, job: AutomationJob) -> int:
        now = _utc_now_iso()
        cursor = self._connection.execute(
            """
            INSERT INTO automation_jobs (
                name,
                enabled,
                job_type,
                schedule_minute,
                schedule_hour,
                schedule_weekdays,
                profile_id,
                remote_path,
                source_local_dir,
                upload_roll_mode,
                upload_fixed_roll,
                keep_last_n,
                last_run_at,
                last_status,
                last_message,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.name,
                1 if job.enabled else 0,
                job.job_type.value,
                int(job.schedule_minute),
                int(job.schedule_hour),
                job.schedule_weekdays,
                job.profile_id,
                job.remote_path,
                job.source_local_dir,
                job.upload_roll_mode,
                job.upload_fixed_roll,
                int(job.keep_last_n),
                job.last_run_at,
                job.last_status,
                job.last_message,
                now,
                now,
            ),
        )
        self._connection.commit()
        return _require_lastrowid(cursor)

    def update_job(self, job: AutomationJob) -> None:
        if job.id is None:
            raise ValueError("job.id is required for update")

        now = _utc_now_iso()
        self._connection.execute(
            """
            UPDATE automation_jobs
            SET
                name = ?,
                enabled = ?,
                job_type = ?,
                schedule_minute = ?,
                schedule_hour = ?,
                schedule_weekdays = ?,
                profile_id = ?,
                remote_path = ?,
                source_local_dir = ?,
                upload_roll_mode = ?,
                upload_fixed_roll = ?,
                keep_last_n = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                job.name,
                1 if job.enabled else 0,
                job.job_type.value,
                int(job.schedule_minute),
                int(job.schedule_hour),
                job.schedule_weekdays,
                job.profile_id,
                job.remote_path,
                job.source_local_dir,
                job.upload_roll_mode,
                job.upload_fixed_roll,
                int(job.keep_last_n),
                now,
                job.id,
            ),
        )
        self._connection.commit()

    def delete_job(self, job_id: int) -> None:
        self._connection.execute("DELETE FROM automation_jobs WHERE id = ?", (job_id,))
        self._connection.commit()

    def record_run(
        self,
        job_id: int,
        status: str,
        message: str,
        started_at: str,
        finished_at: str,
    ) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO automation_runs (job_id, started_at, finished_at, status, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, started_at, finished_at, status, message),
        )
        self._connection.commit()
        return _require_lastrowid(cursor)

    def update_last_state(self, job_id: int, last_run_at: str, status: str, message: str) -> None:
        now = _utc_now_iso()
        self._connection.execute(
            """
            UPDATE automation_jobs
            SET
                last_run_at = ?,
                last_status = ?,
                last_message = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (last_run_at, status, message, now, job_id),
        )
        self._connection.commit()

    def _row_to_job(self, row: sqlite3.Row) -> AutomationJob:
        return AutomationJob(
            id=int(row["id"]),
            name=str(row["name"]),
            enabled=bool(row["enabled"]),
            job_type=AutomationJobType(str(row["job_type"])),
            schedule_minute=int(row["schedule_minute"]),
            schedule_hour=int(row["schedule_hour"]),
            schedule_weekdays=str(row["schedule_weekdays"]),
            profile_id=int(row["profile_id"]) if row["profile_id"] is not None else None,
            remote_path=str(row["remote_path"]) if row["remote_path"] is not None else None,
            source_local_dir=str(row["source_local_dir"]) if row["source_local_dir"] is not None else None,
            upload_roll_mode=str(row["upload_roll_mode"]),
            upload_fixed_roll=int(row["upload_fixed_roll"]) if row["upload_fixed_roll"] is not None else None,
            keep_last_n=int(row["keep_last_n"]),
            last_run_at=str(row["last_run_at"]) if row["last_run_at"] is not None else None,
            last_status=str(row["last_status"]) if row["last_status"] is not None else None,
            last_message=str(row["last_message"]) if row["last_message"] is not None else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_runs_for_job(self, job_id: int) -> list[AutomationRun]:
        rows = self._connection.execute(
            """
            SELECT id, job_id, started_at, finished_at, status, message
            FROM automation_runs
            WHERE job_id = ?
            ORDER BY started_at DESC
            """,
            (job_id,),
        ).fetchall()
        return [
            AutomationRun(
                id=int(row["id"]),
                job_id=int(row["job_id"]),
                started_at=str(row["started_at"]),
                finished_at=str(row["finished_at"]),
                status=str(row["status"]),
                message=str(row["message"]) if row["message"] is not None else None,
            )
            for row in rows
        ]
