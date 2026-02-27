from __future__ import annotations

import asyncio
from datetime import datetime
import ssl
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

import aioftp

from core.profiles.models import Profile
from core.remote.client_base import RemoteEntry


@dataclass(slots=True)
class FTPClient:
    profile: Profile
    password: str
    timeout_seconds: float = 12.0

    async def test_connection(self) -> tuple[bool, str]:
        remote_path = self._normalize_remote_path(self.profile.remote_path)
        try:
            async with self._open_client() as client:
                await asyncio.wait_for(client.list(remote_path).__anext__(), timeout=self.timeout_seconds)
            return True, "ok"
        except StopAsyncIteration:
            return True, "ok"
        except Exception as error:
            return False, str(error)

    async def ensure_dir(self, remote_path: str) -> tuple[bool, str]:
        target = self._normalize_remote_path(remote_path)
        try:
            async with self._open_client() as client:
                await asyncio.wait_for(client.make_directory(target, parents=True), timeout=self.timeout_seconds)
            return True, "ok"
        except Exception as error:
            return False, str(error)

    async def list_dir(self, remote_path: str) -> tuple[bool, str, list[str]]:
        success, message, entries = await self.list_dir_details(remote_path)
        if not success:
            return False, message, []
        return True, "ok", [entry.name for entry in entries]

    async def list_dir_details(self, remote_path: str) -> tuple[bool, str, list[RemoteEntry]]:
        target = self._normalize_remote_path(remote_path)
        entries: list[RemoteEntry] = []
        try:
            async with self._open_client() as client:
                async for path, info in client.list(target):
                    entries.append(self._to_remote_entry(path.name, info))
            return True, "ok", entries
        except Exception as error:
            return False, str(error), []

    async def read_file_bytes(
        self,
        remote_path: str,
        max_bytes: int = 131072,
    ) -> tuple[bool, str, bytes | None]:
        if max_bytes <= 0:
            return False, "invalid max_bytes", None

        target = self._normalize_remote_path(remote_path)
        try:
            async with self._open_client() as client:
                chunks: list[bytes] = []
                total_size = 0

                async with client.download_stream(target) as stream:
                    async for chunk in stream.iter_by_block():
                        total_size += len(chunk)
                        if total_size > max_bytes:
                            return False, "file too large", None
                        chunks.append(bytes(chunk))

            return True, "ok", b"".join(chunks)
        except Exception as error:
            return False, str(error), None

    async def upload_file(self, local_path: Path, remote_path: str) -> tuple[bool, str, int]:
        source = Path(local_path)
        if not source.exists() or not source.is_file():
            return False, "source file missing", 0

        target = self._normalize_remote_path(remote_path)
        target_parent = str(PurePosixPath(target).parent)

        try:
            async with self._open_client() as client:
                await asyncio.wait_for(client.make_directory(target_parent, parents=True), timeout=self.timeout_seconds)
                async with client.upload_stream(target) as stream:
                    with source.open("rb") as handle:
                        total = 0
                        while True:
                            chunk = handle.read(65536)
                            if chunk == b"":
                                break
                            total += len(chunk)
                            await stream.write(chunk)
            return True, "ok", source.stat().st_size
        except Exception as error:
            return False, str(error), 0

    async def upload_bytes(self, remote_path: str, data: bytes) -> tuple[bool, str, int]:
        target = self._normalize_remote_path(remote_path)
        target_parent = str(PurePosixPath(target).parent)

        try:
            async with self._open_client() as client:
                await asyncio.wait_for(client.make_directory(target_parent, parents=True), timeout=self.timeout_seconds)
                async with client.upload_stream(target) as stream:
                    await stream.write(data)
            return True, "ok", len(data)
        except Exception as error:
            return False, str(error), 0

    async def download_file(self, remote_path: str, local_path: Path) -> tuple[bool, str, int]:
        target = self._normalize_remote_path(remote_path)
        local_target = Path(local_path)
        local_target.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with self._open_client() as client:
                total = 0
                async with client.download_stream(target) as stream:
                    with local_target.open("wb") as handle:
                        async for chunk in stream.iter_by_block():
                            total += len(chunk)
                            handle.write(chunk)
            return True, "ok", total
        except Exception as error:
            return False, str(error), 0

    async def file_exists(self, remote_path: str) -> tuple[bool, str, bool]:
        normalized = self._normalize_remote_path(remote_path)
        parent = str(PurePosixPath(normalized).parent)
        target_name = PurePosixPath(normalized).name

        try:
            async with self._open_client() as client:
                async for path, info in client.list(parent):
                    if path.name != target_name:
                        continue
                    entry = self._to_remote_entry(path.name, info)
                    return True, "ok", entry.is_file
            return True, "ok", False
        except Exception as error:
            return False, str(error), False

    def _normalize_remote_path(self, remote_path: str) -> str:
        normalized = "/" + "/".join(part for part in remote_path.strip().split("/") if part)
        return normalized if normalized != "" else "/"

    def _to_remote_entry(self, name: str, info: Mapping[str, object]) -> RemoteEntry:
        entry_type = str(info.get("type", "")).lower()
        is_file = entry_type == "file"

        size_bytes: int | None = None
        size_raw = info.get("size")
        if isinstance(size_raw, (int, str, float)):
            try:
                size_bytes = int(size_raw)
            except (TypeError, ValueError):
                size_bytes = None

        modified_at: datetime | None = None
        modify_raw = info.get("modify")
        if isinstance(modify_raw, str) and len(modify_raw) >= 14:
            try:
                modified_at = datetime.strptime(modify_raw[:14], "%Y%m%d%H%M%S")
            except ValueError:
                modified_at = None

        return RemoteEntry(
            name=name,
            is_file=is_file,
            size_bytes=size_bytes,
            modified_at=modified_at,
        )

    def _ssl_context(self) -> ssl.SSLContext | None:
        if self.profile.protocol != "ftps":
            return None
        return ssl.create_default_context()

    def _open_client(self):
        return aioftp.Client.context(
            host=self.profile.host,
            port=self.profile.port,
            user=self.profile.username,
            password=self.password,
            ssl=self._ssl_context(),
            connection_timeout=self.timeout_seconds,
            socket_timeout=self.timeout_seconds,
            passive_commands=("pasv",) if self.profile.passive_mode else (),
            path_timeout=self.timeout_seconds,
        )
