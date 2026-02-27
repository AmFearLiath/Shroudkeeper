from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from pathlib import Path
import shutil

from PySide6.QtCore import QObject, Signal

from core.automations.models import AutomationExecutionResult, AutomationJob
from core.backups.backup_service import create_server_backup
from core.config import AppConfig
from core.profiles.models import Profile
from i18n.i18n import tr


class ServerBackupJobWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        config: AppConfig,
        job: AutomationJob,
        profile: Profile,
        password: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self._config = config
        self._job = job
        self._profile = profile
        self._password = password
        self._logger = logger

    def run(self) -> None:
        try:
            result = asyncio.run(self._run_async())
            self.finished.emit(result)
        except Exception as error:
            self.error.emit(str(error))

    async def _run_async(self) -> AutomationExecutionResult:
        remote_path = self._job.remote_path.strip() if self._job.remote_path else self._profile.remote_path

        backup_result = await create_server_backup(
            profile=self._profile,
            password=self._password,
            remote_path=remote_path,
            backup_root=Path(self._config.get_backup_root_dir()),
            logger=self._logger,
            backup_zip_enabled=self._config.get_backup_zip_enabled(),
            backup_keep_uncompressed=self._config.get_backup_keep_uncompressed(),
            progress=None,
        )

        if not backup_result.success:
            return AutomationExecutionResult(status="failed", message=backup_result.message)

        self._apply_retention(self._job.keep_last_n)
        return AutomationExecutionResult(status="success", message=tr("automations.status.success"))

    def _apply_retention(self, keep_last_n: int) -> None:
        keep = max(1, int(keep_last_n))
        base_dir = Path(self._config.get_backup_root_dir()) / "server"
        if not base_dir.exists() or not base_dir.is_dir():
            return

        profile_key = _sanitize_name(self._profile.name)
        marker = f"__SRV__{profile_key}__ServerWorld"

        candidates: list[Path] = []
        for path in base_dir.iterdir():
            if marker in path.name:
                candidates.append(path)

        candidates.sort(key=lambda item: item.name, reverse=True)
        for old_path in candidates[keep:]:
            try:
                if old_path.is_dir():
                    shutil.rmtree(old_path)
                elif old_path.exists():
                    old_path.unlink()
            except OSError:
                continue


def _sanitize_name(value: str, max_len: int = 50) -> str:
    invalid = '<>:"/\\|?*'
    sanitized = "".join("_" if char in invalid else char for char in value).strip()
    sanitized = " ".join(sanitized.split())
    if sanitized == "":
        sanitized = "backup"
    return sanitized[:max_len]
