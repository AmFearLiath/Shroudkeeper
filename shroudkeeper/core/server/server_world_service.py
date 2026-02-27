from __future__ import annotations

import json
import logging
from pathlib import PurePosixPath

from core.remote.client_base import RemoteClient
from core.server.server_models import ServerRoll, ServerScanResult
from i18n.i18n import tr


class ServerWorldService:
    SERVER_WORLD_ID = "3ad85aea"
    MAX_ROLLS = 10
    INDEX_MAX_BYTES = 64 * 1024

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("shroudkeeper.server")

    async def scan_server_world(self, client: RemoteClient, remote_root: str) -> ServerScanResult:
        normalized_root = self._normalize_remote_path(remote_root)

        list_success, list_message, entries = await client.list_dir_details(normalized_root)
        if not list_success:
            raise RuntimeError(list_message)

        entry_by_name = {entry.name: entry for entry in entries}

        rolls: list[ServerRoll] = []
        for roll_index in range(self.MAX_ROLLS):
            file_name = self.SERVER_WORLD_ID if roll_index == 0 else f"{self.SERVER_WORLD_ID}-{roll_index}"
            entry = entry_by_name.get(file_name)
            rolls.append(
                ServerRoll(
                    roll_index=roll_index,
                    file_name=file_name,
                    exists=entry is not None and entry.is_file,
                    size_bytes=entry.size_bytes if entry is not None and entry.is_file else None,
                    modified_at=entry.modified_at if entry is not None and entry.is_file else None,
                )
            )

        latest = None
        warnings: list[str] = []
        index_name = f"{self.SERVER_WORLD_ID}-index"

        if index_name not in entry_by_name:
            warnings.append(tr("server.warning.index_missing"))
        else:
            index_path = self._join_remote_path(normalized_root, index_name)
            read_success, read_message, payload = await client.read_file_bytes(index_path, max_bytes=self.INDEX_MAX_BYTES)
            if not read_success or payload is None:
                warnings.append(tr("server.warning.index_read_failed", error=read_message))
            else:
                latest = self._parse_latest(payload)
                if latest is None:
                    warnings.append(tr("server.warning.index_invalid"))

        return ServerScanResult(
            world_id_hex=self.SERVER_WORLD_ID,
            remote_root=normalized_root,
            latest=latest,
            rolls=rolls,
            warnings=warnings,
        )

    def _parse_latest(self, payload: bytes) -> int | None:
        try:
            decoded = payload.decode("utf-8")
            loaded = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(loaded, dict):
            return None

        latest = loaded.get("latest")
        if isinstance(latest, int) and 0 <= latest <= 9:
            return latest

        return None

    def _normalize_remote_path(self, remote_path: str) -> str:
        normalized = "/" + "/".join(part for part in remote_path.strip().split("/") if part)
        return str(PurePosixPath(normalized if normalized != "" else "/"))

    def _join_remote_path(self, root: str, name: str) -> str:
        return str(PurePosixPath(root) / name)

    async def write_latest(self, client: RemoteClient, remote_root: str, latest: int) -> tuple[bool, str]:
        if latest < 0 or latest >= self.MAX_ROLLS:
            return False, "latest must be between 0 and 9"

        normalized_root = self._normalize_remote_path(remote_root)
        index_name = f"{self.SERVER_WORLD_ID}-index"
        index_path = self._join_remote_path(normalized_root, index_name)
        payload = json.dumps({"latest": latest}, ensure_ascii=False, indent=2).encode("utf-8")

        success, message, _bytes_written = await client.upload_bytes(index_path, payload)
        if not success:
            return False, message

        return True, "ok"
