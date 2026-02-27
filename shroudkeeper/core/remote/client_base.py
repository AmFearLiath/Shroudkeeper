from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class RemoteEntry:
    name: str
    is_file: bool
    size_bytes: int | None
    modified_at: datetime | None


class RemoteClient(Protocol):
    async def test_connection(self) -> tuple[bool, str]: ...

    async def ensure_dir(self, remote_path: str) -> tuple[bool, str]: ...

    async def list_dir(self, remote_path: str) -> tuple[bool, str, list[str]]: ...

    async def list_dir_details(self, remote_path: str) -> tuple[bool, str, list[RemoteEntry]]: ...

    async def read_file_bytes(
        self,
        remote_path: str,
        max_bytes: int = 131072,
    ) -> tuple[bool, str, bytes | None]: ...

    async def upload_file(self, local_path: Path, remote_path: str) -> tuple[bool, str, int]: ...

    async def upload_bytes(self, remote_path: str, data: bytes) -> tuple[bool, str, int]: ...

    async def download_file(self, remote_path: str, local_path: Path) -> tuple[bool, str, int]: ...

    async def file_exists(self, remote_path: str) -> tuple[bool, str, bool]: ...
