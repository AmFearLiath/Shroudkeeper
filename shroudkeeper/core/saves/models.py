from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class SaveRoll:
    roll_index: int
    path: Path
    exists: bool
    size_bytes: int | None
    modified_at: datetime | None


@dataclass(slots=True)
class SaveSlot:
    slot_number: int
    world_id_hex: str
    root_dir: Path
    rolls: list[SaveRoll]
    index_path: Path
    latest: int | None
    display_name: str
    world_name_source: str
    last_modified: datetime | None
    total_size_bytes: int


@dataclass(slots=True)
class SaveScanResult:
    root: Path
    slots: list[SaveSlot]
    warnings: list[str]
