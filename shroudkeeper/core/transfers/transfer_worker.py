from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.profiles.models import Profile
from core.remote.client_factory import create_client
from core.transfers.execute_local import copy_file_atomic, write_local_latest_index
from core.transfers.execute_remote import download_remote_file_to_local_atomic, join_remote, upload_index_latest, upload_local_file
from core.transfers.transfer_models import TransferDirection, TransferPlan, TransferResult
from i18n.i18n import tr


class TransferWorker(QObject):
    progress = Signal(int, str)
    success = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        plan: TransferPlan,
        logger: logging.Logger,
        profile: Profile | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__()
        self._plan = plan
        self._logger = logger
        self._profile = profile
        self._password = password

    def run(self) -> None:
        try:
            result = asyncio.run(self._execute())
            self.success.emit(result)
        except Exception as error:
            self.error.emit(str(error))

    async def _execute(self) -> TransferResult:
        self.progress.emit(5, tr("transfers.progress.preparing"))

        if self._plan.direction == TransferDirection.SP_TO_SP:
            return await self._execute_sp_to_sp()

        if self._profile is None or self._password is None or self._password.strip() == "":
            raise RuntimeError(tr("transfers.error.no_active_profile"))

        client = create_client(profile=self._profile, password=self._password, logger=self._logger)

        if self._plan.direction == TransferDirection.SP_TO_SERVER:
            return await self._execute_sp_to_server(client)

        if self._plan.direction == TransferDirection.SERVER_TO_SP:
            return await self._execute_server_to_sp(client)

        raise RuntimeError(tr("transfers.error.invalid_direction"))

    async def _execute_sp_to_sp(self) -> TransferResult:
        source_root = Path(self._plan.source_root)
        target_root = Path(self._plan.target_root)

        bytes_copied = 0
        files_copied = 0

        for src_name, dst_name in self._plan.files:
            self.progress.emit(40, tr("transfers.progress.copying"))
            bytes_copied += copy_file_atomic(source_root / src_name, target_root / dst_name)
            files_copied += 1

        self.progress.emit(85, tr("transfers.progress.writing_index"))
        write_local_latest_index(Path(self._plan.index_target_path), self._plan.roll_index)

        self.progress.emit(100, tr("transfers.progress.done"))
        return TransferResult(success=True, message="ok", bytes_copied=bytes_copied, files_copied=files_copied)

    async def _execute_sp_to_server(self, client) -> TransferResult:
        source_root = Path(self._plan.source_root)
        target_root = str(self._plan.target_root)

        bytes_copied = 0
        files_copied = 0

        for src_name, dst_name in self._plan.files:
            self.progress.emit(40, tr("transfers.progress.copying"))
            remote_file = join_remote(target_root, dst_name)
            bytes_copied += await upload_local_file(client, source_root / src_name, remote_file)
            files_copied += 1

        self.progress.emit(85, tr("transfers.progress.writing_index"))
        await upload_index_latest(client, str(self._plan.index_target_path), self._plan.roll_index)

        self.progress.emit(100, tr("transfers.progress.done"))
        return TransferResult(success=True, message="ok", bytes_copied=bytes_copied, files_copied=files_copied)

    async def _execute_server_to_sp(self, client) -> TransferResult:
        source_root = str(self._plan.source_root)
        target_root = Path(self._plan.target_root)

        bytes_copied = 0
        files_copied = 0

        for src_name, dst_name in self._plan.files:
            self.progress.emit(40, tr("transfers.progress.copying"))
            remote_file = join_remote(source_root, src_name)
            bytes_copied += await download_remote_file_to_local_atomic(client, remote_file, target_root / dst_name)
            files_copied += 1

        self.progress.emit(85, tr("transfers.progress.writing_index"))
        write_local_latest_index(Path(self._plan.index_target_path), self._plan.roll_index)

        self.progress.emit(100, tr("transfers.progress.done"))
        return TransferResult(success=True, message="ok", bytes_copied=bytes_copied, files_copied=files_copied)
