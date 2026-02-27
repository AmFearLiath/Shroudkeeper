from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from core.saves.constants import MAX_ROLLS
from core.saves.index_service import IndexFileService
from core.saves.models import SaveRoll, SaveScanResult, SaveSlot
from core.saves.world_slots import WORLD_SLOT_MAPPING
from core.worldname.mapping import get_world_name_with_source
from i18n.i18n import tr


class SaveScannerService:
    def __init__(self, logger: logging.Logger | None = None, index_service: IndexFileService | None = None) -> None:
        self._logger = logger or logging.getLogger("shroudkeeper.scanner")
        self._index_service = index_service or IndexFileService(self._logger)

    def scan_singleplayer(self, root: Path) -> SaveScanResult:
        safe_root = root.expanduser().resolve()
        effective_root = self._resolve_effective_root(safe_root)
        self._logger.info("Scanning Singleplayer root: %s", effective_root)

        warnings: list[str] = []
        slots: list[SaveSlot] = []
        missing_latest_slots: list[int] = []
        world_name_cache: dict[str, tuple[str | None, str]] = {}

        if not effective_root.exists():
            warnings.append(tr("dashboard.warning.root_missing", root=effective_root))
            self._logger.warning("Save root does not exist")

        for slot_number in range(1, 11):
            world_id = WORLD_SLOT_MAPPING[slot_number]
            slot, has_missing_latest = self._scan_slot(
                effective_root,
                slot_number,
                world_id,
                warnings,
                world_name_cache,
            )
            if slot is None:
                continue
            slots.append(slot)
            if has_missing_latest:
                missing_latest_slots.append(slot_number)

        if missing_latest_slots:
            warnings.append(
                tr(
                    "dashboard.warning.latest_missing_grouped",
                    slots=self._format_slot_ranges(missing_latest_slots),
                )
            )

        self._logger.info("Scan finished: slots=%s warnings=%s", len(slots), len(warnings))
        return SaveScanResult(root=effective_root, slots=slots, warnings=warnings)

    def _resolve_effective_root(self, root: Path) -> Path:
        remote_root = (root / "remote").resolve()

        root_has_saves = self._contains_expected_save_files(root)
        remote_has_saves = self._contains_expected_save_files(remote_root)

        if remote_root.exists() and remote_has_saves and not root_has_saves:
            self._logger.info(tr("dashboard.scan.root_switched_remote", root=remote_root))
            return remote_root

        return root

    def _contains_expected_save_files(self, root: Path) -> bool:
        if not root.exists() or not root.is_dir():
            return False

        for world_hex in WORLD_SLOT_MAPPING.values():
            if (root / world_hex).is_file() or (root / f"{world_hex}-index").is_file():
                return True
        return False

    def _scan_slot(
        self,
        root: Path,
        slot_number: int,
        world_id: str,
        warnings: list[str],
        world_name_cache: dict[str, tuple[str | None, str]],
    ) -> tuple[SaveSlot | None, bool]:
        root_dir = root

        rolls: list[SaveRoll] = []
        existing_rolls_count = 0
        for roll_index in range(MAX_ROLLS):
            file_name = world_id if roll_index == 0 else f"{world_id}-{roll_index}"
            roll_path = root_dir / file_name
            exists = roll_path.exists() and roll_path.is_file()

            size_bytes: int | None = None
            modified_at: datetime | None = None

            if exists:
                existing_rolls_count += 1
                try:
                    stat_info = roll_path.stat()
                    size_bytes = int(stat_info.st_size)
                    modified_at = datetime.fromtimestamp(stat_info.st_mtime)
                except OSError:
                    warnings.append(tr("dashboard.warning.file_stat_failed", file_name=roll_path.name))

            rolls.append(
                SaveRoll(
                    roll_index=roll_index,
                    path=roll_path,
                    exists=exists,
                    size_bytes=size_bytes,
                    modified_at=modified_at,
                )
            )

        if existing_rolls_count == 0:
            self._logger.info("Slot %s empty - skipped", slot_number)
            return None, False

        index_path = root_dir / f"{world_id}-index"
        latest = self._index_service.read_latest(index_path)
        has_missing_latest = latest is None

        display_name, world_name_source = self._load_slot_name(
            root_dir,
            world_id,
            slot_number,
            world_name_cache,
        )
        last_modified = self._compute_last_modified(rolls)
        total_size = sum(roll.size_bytes or 0 for roll in rolls if roll.exists)

        self._logger.info(
            "Slot %s scanned: world=%s existing_rolls=%s latest=%s",
            slot_number,
            world_id,
            existing_rolls_count,
            latest,
        )

        return (
            SaveSlot(
                slot_number=slot_number,
                world_id_hex=world_id,
                root_dir=root_dir,
                rolls=rolls,
                index_path=index_path,
                latest=latest,
                display_name=display_name,
                world_name_source=world_name_source,
                last_modified=last_modified,
                total_size_bytes=total_size,
            ),
            has_missing_latest,
        )

    def _load_slot_name(
        self,
        root: Path,
        world_id: str,
        slot_number: int,
        world_name_cache: dict[str, tuple[str | None, str]],
    ) -> tuple[str, str]:
        prefix = world_id.lower()
        cached = world_name_cache.get(prefix)
        if cached is None:
            cached = get_world_name_with_source(prefix=prefix, root_dir=root)
            world_name_cache[prefix] = cached

        world_name, source = cached
        if world_name:
            return world_name, source

        return tr("dashboard.world_slot_name", slot=slot_number), "fallback"

    @staticmethod
    def _compute_last_modified(rolls: list[SaveRoll]) -> datetime | None:
        values = [roll.modified_at for roll in rolls if roll.modified_at is not None]
        if not values:
            return None
        return max(values)

    @staticmethod
    def _format_slot_ranges(slots: list[int]) -> str:
        if not slots:
            return ""

        ordered = sorted(set(slots))
        ranges: list[str] = []
        start = ordered[0]
        end = ordered[0]

        for current in ordered[1:]:
            if current == end + 1:
                end = current
                continue

            ranges.append(f"{start}-{end}" if start != end else f"{start}")
            start = current
            end = current

        ranges.append(f"{start}-{end}" if start != end else f"{start}")
        return ", ".join(ranges)
