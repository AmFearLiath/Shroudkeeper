from __future__ import annotations

from datetime import datetime, timezone
import logging
import sqlite3

from PySide6.QtCore import QObject, QThread, Signal

from core.automations.models import AutomationExecutionResult, AutomationJob, AutomationJobType
from core.automations.workers.scheduled_upload_job_worker import ScheduledUploadJobWorker
from core.automations.workers.server_backup_job_worker import ServerBackupJobWorker
from core.config import AppConfig
from core.profiles.credentials import CredentialService
from storage.repositories import AutomationJobRepository, ProfileRepository
from i18n.i18n import tr


class AutomationRunner(QObject):
    job_started = Signal(int)
    job_finished = Signal(int, str, str)

    def __init__(
        self,
        connection: sqlite3.Connection,
        config: AppConfig,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self._connection = connection
        self._config = config
        self._logger = logger
        self._job_repo = AutomationJobRepository(connection)
        self._profile_repo = ProfileRepository(connection)
        self._credential_service = CredentialService()
        self._running_threads: dict[int, QThread] = {}
        self._run_started_at: dict[int, str] = {}

    def run_job_id(self, job_id: int) -> None:
        job = self._job_repo.get_job(job_id)
        if job is None:
            return
        self.run_job(job)

    def run_job_now(self, job_id: int) -> None:
        self.run_job_id(job_id)

    def run_job(self, job: AutomationJob) -> None:
        if job.id is None:
            return

        if job.id in self._running_threads:
            self._finalize_job(job.id, "skipped", tr("automations.error.already_running"))
            return

        if job.profile_id is None:
            self._finalize_job(job.id, "failed", tr("automations.error.profile_required"))
            return

        profile = self._profile_repo.get_profile(job.profile_id)
        if profile is None or profile.id is None:
            self._finalize_job(job.id, "failed", tr("automations.error.profile_required"))
            return

        password = self._credential_service.get_password(profile.id, profile.username)
        if password is None or password.strip() == "":
            self._finalize_job(job.id, "failed", tr("automations.error.missing_credentials"))
            return

        thread = QThread(self)
        worker = self._create_worker(job=job, profile=profile, password=password)
        if worker is None:
            self._finalize_job(job.id, "failed", tr("automations.status.failed"))
            return

        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(
            lambda result, job_id=job.id: self._on_worker_finished(job_id, result)
        )
        worker.error.connect(
            lambda message, job_id=job.id: self._on_worker_error(job_id, message)
        )
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda job_id=job.id: self._cleanup_job(job_id))

        self._running_threads[job.id] = thread
        self._run_started_at[job.id] = _utc_now_iso()
        self.job_started.emit(job.id)
        thread.start()

    def _create_worker(self, job: AutomationJob, profile, password: str):
        if job.job_type == AutomationJobType.SERVER_BACKUP:
            return ServerBackupJobWorker(
                config=self._config,
                job=job,
                profile=profile,
                password=password,
                logger=self._logger,
            )

        if job.job_type == AutomationJobType.SCHEDULED_UPLOAD:
            return ScheduledUploadJobWorker(
                config=self._config,
                job=job,
                profile=profile,
                password=password,
                logger=self._logger,
            )

        return None

    def _on_worker_finished(self, job_id: int, result: object) -> None:
        if isinstance(result, AutomationExecutionResult):
            self._finalize_job(job_id, result.status, result.message)
            return

        self._finalize_job(job_id, "failed", tr("automations.status.failed"))

    def _on_worker_error(self, job_id: int, message: str) -> None:
        self._finalize_job(job_id, "failed", message)

    def _finalize_job(self, job_id: int, status: str, message: str) -> None:
        started_at = self._run_started_at.get(job_id, _utc_now_iso())
        finished_at = _utc_now_iso()
        safe_message = message.strip() if message.strip() != "" else tr("automations.status.failed")

        self._job_repo.update_last_state(job_id=job_id, last_run_at=finished_at, status=status, message=safe_message)
        self._job_repo.record_run(
            job_id=job_id,
            status=status,
            message=safe_message,
            started_at=started_at,
            finished_at=finished_at,
        )

        self.job_finished.emit(job_id, status, safe_message)

    def _cleanup_job(self, job_id: int) -> None:
        self._running_threads.pop(job_id, None)
        self._run_started_at.pop(job_id, None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
