from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path, PurePosixPath
import stat

import asyncssh

from core.profiles.models import Profile
from core.remote.client_base import RemoteEntry


class SFTPClient:
    def __init__(self, profile: Profile, password: str, timeout_seconds: float = 12.0) -> None:
        self._profile = profile
        self._password = password
        self._timeout_seconds = timeout_seconds

    async def test_connection(self) -> tuple[bool, str]:
        remote_path = self._normalize_remote_path(self._profile.remote_path)
        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.listdir(remote_path), timeout=self._timeout_seconds)
            return True, "ok"
        except Exception as error:
            return False, str(error)

    async def ensure_dir(self, remote_path: str) -> tuple[bool, str]:
        target = self._normalize_remote_path(remote_path)
        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.makedirs(target, exist_ok=True), timeout=self._timeout_seconds)
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
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                async for item in sftp.scandir(target):
                    attrs = item.attrs
                    permissions = attrs.permissions
                    is_file = bool(permissions is not None and stat.S_ISREG(permissions))

                    size_bytes = int(attrs.size) if attrs.size is not None else None
                    modified_at = datetime.fromtimestamp(attrs.mtime) if attrs.mtime is not None else None

                    entries.append(
                        RemoteEntry(
                            name=str(item.filename),
                            is_file=is_file,
                            size_bytes=size_bytes,
                            modified_at=modified_at,
                        )
                    )

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
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                async with sftp.open(target, "rb") as remote_file:
                    payload = await asyncio.wait_for(remote_file.read(max_bytes + 1), timeout=self._timeout_seconds)

            if len(payload) > max_bytes:
                return False, "file too large", None

            return True, "ok", bytes(payload)
        except Exception as error:
            return False, str(error), None

    async def upload_file(self, local_path: Path, remote_path: str) -> tuple[bool, str, int]:
        source = Path(local_path)
        if not source.exists() or not source.is_file():
            return False, "source file missing", 0

        target = self._normalize_remote_path(remote_path)
        parent = str(PurePosixPath(target).parent)

        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.makedirs(parent, exist_ok=True), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.put(str(source), target), timeout=self._timeout_seconds)
            return True, "ok", source.stat().st_size
        except Exception as error:
            return False, str(error), 0

    async def upload_bytes(self, remote_path: str, data: bytes) -> tuple[bool, str, int]:
        target = self._normalize_remote_path(remote_path)
        parent = str(PurePosixPath(target).parent)

        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.makedirs(parent, exist_ok=True), timeout=self._timeout_seconds)
                async with sftp.open(target, "wb") as remote_file:
                    await asyncio.wait_for(remote_file.write(data), timeout=self._timeout_seconds)
            return True, "ok", len(data)
        except Exception as error:
            return False, str(error), 0

    async def download_file(self, remote_path: str, local_path: Path) -> tuple[bool, str, int]:
        source = self._normalize_remote_path(remote_path)
        target = Path(local_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                await asyncio.wait_for(sftp.get(source, str(target)), timeout=self._timeout_seconds)
            return True, "ok", target.stat().st_size
        except Exception as error:
            return False, str(error), 0

    async def file_exists(self, remote_path: str) -> tuple[bool, str, bool]:
        source = self._normalize_remote_path(remote_path)
        try:
            async with self._open_connection() as connection:
                sftp = await asyncio.wait_for(connection.start_sftp_client(), timeout=self._timeout_seconds)
                attrs = await asyncio.wait_for(sftp.stat(source), timeout=self._timeout_seconds)

            permissions = attrs.permissions
            if permissions is None:
                return True, "ok", True

            return True, "ok", bool(stat.S_ISREG(permissions))
        except asyncssh.SFTPNoSuchFile:
            return True, "ok", False
        except Exception as error:
            return False, str(error), False

    def _open_connection(self):
        known_hosts = None if not self._profile.verify_host_key else ()
        return asyncssh.connect(
            host=self._profile.host,
            port=self._profile.port,
            username=self._profile.username,
            password=self._password,
            known_hosts=known_hosts,
            login_timeout=self._timeout_seconds,
        )

    def _normalize_remote_path(self, remote_path: str) -> str:
        normalized = "/" + "/".join(part for part in remote_path.strip().split("/") if part)
        return str(PurePosixPath(normalized if normalized != "" else "/"))
