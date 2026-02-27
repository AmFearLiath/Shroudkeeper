from __future__ import annotations

from pathlib import Path, PurePosixPath

from core.saves.models import SaveSlot
from core.saves.world_slots import WORLD_SLOT_MAPPING
from core.transfers.transfer_models import TransferDirection, TransferPlan


SERVER_WORLD_HEX = "3ad85aea"


def build_plan_sp_to_sp(source_slot: SaveSlot, target_slot: int, roll_index: int) -> TransferPlan:
    _validate_roll_index(roll_index)
    target_world_hex = _slot_world_hex(target_slot)

    source_name = _roll_file_name(source_slot.world_id_hex, roll_index)
    target_name = _roll_file_name(target_world_hex, roll_index)

    root = source_slot.root_dir
    target_index = root / f"{target_world_hex}-index"

    return TransferPlan(
        direction=TransferDirection.SP_TO_SP,
        source_desc=f"SP {source_slot.slot_number}",
        target_desc=f"SP {target_slot}",
        source_world_hex=source_slot.world_id_hex,
        target_world_hex=target_world_hex,
        source_root=root,
        target_root=root,
        roll_index=roll_index,
        files=[(source_name, target_name)],
        index_target_path=target_index,
    )


def build_plan_sp_to_server(source_slot: SaveSlot, roll_index: int, server_root: str = "/") -> TransferPlan:
    _validate_roll_index(roll_index)
    normalized_server_root = _normalize_remote_root(server_root)

    source_name = _roll_file_name(source_slot.world_id_hex, roll_index)
    target_name = _roll_file_name(SERVER_WORLD_HEX, roll_index)

    return TransferPlan(
        direction=TransferDirection.SP_TO_SERVER,
        source_desc=f"SP {source_slot.slot_number}",
        target_desc="Server",
        source_world_hex=source_slot.world_id_hex,
        target_world_hex=SERVER_WORLD_HEX,
        source_root=source_slot.root_dir,
        target_root=normalized_server_root,
        roll_index=roll_index,
        files=[(source_name, target_name)],
        index_target_path=_join_remote(normalized_server_root, f"{SERVER_WORLD_HEX}-index"),
    )


def build_plan_server_to_sp(target_slot: int, roll_index: int, local_root: Path, server_root: str = "/") -> TransferPlan:
    _validate_roll_index(roll_index)
    target_world_hex = _slot_world_hex(target_slot)
    normalized_server_root = _normalize_remote_root(server_root)
    local_root_path = Path(local_root)

    source_name = _roll_file_name(SERVER_WORLD_HEX, roll_index)
    target_name = _roll_file_name(target_world_hex, roll_index)

    return TransferPlan(
        direction=TransferDirection.SERVER_TO_SP,
        source_desc="Server",
        target_desc=f"SP {target_slot}",
        source_world_hex=SERVER_WORLD_HEX,
        target_world_hex=target_world_hex,
        source_root=normalized_server_root,
        target_root=local_root_path,
        roll_index=roll_index,
        files=[(source_name, target_name)],
        index_target_path=local_root_path / f"{target_world_hex}-index",
    )


def _roll_file_name(world_hex: str, roll_index: int) -> str:
    if roll_index == 0:
        return world_hex
    return f"{world_hex}-{roll_index}"


def _slot_world_hex(slot_number: int) -> str:
    if slot_number not in WORLD_SLOT_MAPPING:
        raise ValueError("invalid target slot")
    return WORLD_SLOT_MAPPING[slot_number]


def _validate_roll_index(roll_index: int) -> None:
    if roll_index < 0 or roll_index > 9:
        raise ValueError("roll_index must be between 0 and 9")


def _normalize_remote_root(remote_root: str) -> str:
    normalized = "/" + "/".join(part for part in remote_root.strip().split("/") if part)
    return str(PurePosixPath(normalized if normalized != "" else "/"))


def _join_remote(root: str, name: str) -> str:
    return str(PurePosixPath(root) / name)
