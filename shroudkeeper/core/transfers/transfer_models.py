from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TransferDirection(str, Enum):
    SP_TO_SP = "sp_to_sp"
    SP_TO_SERVER = "sp_to_server"
    SERVER_TO_SP = "server_to_sp"


@dataclass(slots=True)
class TransferPlan:
    direction: TransferDirection
    source_desc: str
    target_desc: str
    source_world_hex: str
    target_world_hex: str
    source_root: Path | str
    target_root: Path | str
    roll_index: int
    files: list[tuple[str, str]]
    index_target_path: Path | str


@dataclass(slots=True)
class TransferResult:
    success: bool
    message: str
    bytes_copied: int
    files_copied: int
