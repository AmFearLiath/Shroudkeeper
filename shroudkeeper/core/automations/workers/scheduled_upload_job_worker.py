from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path, PurePosixPath
import re

from PySide6.QtCore import QObject, Signal

from core.automations.models import AutomationExecutionResult, AutomationJob
from core.config import AppConfig
from core.profiles.models import Profile
from core.remote.client_factory import create_client
from core.transfers.execute_remote import upload_index_latest, upload_local_file
from i18n.i18n import tr


SERVER_WORLD_HEX = "3ad85aea"
ROLL_FILE_REGEX = re.compile(r"^(?P<world>[0-9a-fA-F]{8})(?:-(?P<roll>[0-9]))?$")
INDEX_FILE_REGEX = re.compile(r"^(?P<world>[0-9a-fA-F]{8})-index$")


class ScheduledUploadJobWorker(QObject):
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
        if self._job.source_local_dir is None or self._job.source_local_dir.strip() == "":
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))

        source_dir = Path(self._job.source_local_dir).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))

        source_info = self._detect_source_files(source_dir)
        if source_info is None:
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))

        selected_roll = self._select_roll(source_info)
        if selected_roll is None:
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))

        files_by_roll = source_info.get("files_by_roll")
        if not isinstance(files_by_roll, dict):
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))

        local_roll_file = files_by_roll.get(selected_roll)
        if not isinstance(local_roll_file, Path):
            return AutomationExecutionResult(status="failed", message=tr("automations.error.invalid_source_folder"))
        remote_root = self._job.remote_path.strip() if self._job.remote_path else self._profile.remote_path
        remote_root = str(PurePosixPath("/" + "/".join(part for part in remote_root.split("/") if part)))
        if remote_root.strip() == "":
            remote_root = "/"

        target_roll_name = SERVER_WORLD_HEX if selected_roll == 0 else f"{SERVER_WORLD_HEX}-{selected_roll}"
        target_roll_path = str(PurePosixPath(remote_root) / target_roll_name)
        target_index_path = str(PurePosixPath(remote_root) / f"{SERVER_WORLD_HEX}-index")

        client = create_client(profile=self._profile, password=self._password, logger=self._logger)
        ensure_success, ensure_message = await client.ensure_dir(remote_root)
        if not ensure_success:
            return AutomationExecutionResult(status="failed", message=ensure_message)

        try:
            await upload_local_file(client, local_roll_file, target_roll_path)
            await upload_index_latest(client, target_index_path, selected_roll)
        except Exception as error:
            return AutomationExecutionResult(status="failed", message=str(error))

        return AutomationExecutionResult(status="success", message=tr("automations.status.success"))

    def _detect_source_files(self, source_dir: Path) -> dict[str, object] | None:
        worlds: dict[str, dict[str, object]] = {}

        for file_path in source_dir.iterdir():
            if not file_path.is_file():
                continue

            index_match = INDEX_FILE_REGEX.match(file_path.name)
            if index_match is not None:
                world = index_match.group("world").lower()
                data = worlds.setdefault(world, {"files_by_roll": {}, "index_path": None})
                data["index_path"] = file_path
                continue

            roll_match = ROLL_FILE_REGEX.match(file_path.name)
            if roll_match is None:
                continue

            world = roll_match.group("world").lower()
            roll_raw = roll_match.group("roll")
            roll = int(roll_raw) if roll_raw is not None else 0
            data = worlds.setdefault(world, {"files_by_roll": {}, "index_path": None})
            files_by_roll = data["files_by_roll"]
            if isinstance(files_by_roll, dict):
                files_by_roll[roll] = file_path

        if len(worlds) == 0:
            return None

        if len(worlds) == 1:
            world_hex = next(iter(worlds.keys()))
            world_data = worlds[world_hex]
            return {
                "world_hex": world_hex,
                "files_by_roll": world_data["files_by_roll"],
                "index_path": world_data["index_path"],
            }

        if SERVER_WORLD_HEX in worlds:
            world_data = worlds[SERVER_WORLD_HEX]
            return {
                "world_hex": SERVER_WORLD_HEX,
                "files_by_roll": world_data["files_by_roll"],
                "index_path": world_data["index_path"],
            }

        return None

    def _select_roll(self, source_info: dict[str, object]) -> int | None:
        files_by_roll = source_info.get("files_by_roll")
        if not isinstance(files_by_roll, dict) or len(files_by_roll) == 0:
            return None

        available_rolls = sorted(key for key in files_by_roll.keys() if isinstance(key, int))
        if len(available_rolls) == 0:
            return None

        if self._job.upload_roll_mode == "fixed":
            fixed_roll = self._job.upload_fixed_roll
            if fixed_roll is None:
                return None
            return int(fixed_roll) if int(fixed_roll) in available_rolls else None

        index_path = source_info.get("index_path")
        latest_roll = self._read_latest_roll(index_path if isinstance(index_path, Path) else None)
        if latest_roll is not None and latest_roll in available_rolls:
            return latest_roll

        return available_rolls[-1]

    def _read_latest_roll(self, index_path: Path | None) -> int | None:
        if index_path is None or not index_path.exists() or not index_path.is_file():
            return None

        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict):
            return None

        value = payload.get("latest")
        if not isinstance(value, int):
            return None
        if value < 0 or value > 9:
            return None
        return value
