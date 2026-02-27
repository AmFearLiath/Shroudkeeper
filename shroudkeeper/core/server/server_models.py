from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ServerRoll:
    roll_index: int
    file_name: str
    exists: bool
    size_bytes: int | None
    modified_at: datetime | None


@dataclass(slots=True)
class ServerScanResult:
    world_id_hex: str
    remote_root: str
    latest: int | None
    rolls: list[ServerRoll]
    warnings: list[str]
