from __future__ import annotations

import json
import logging
from pathlib import Path


_logger = logging.getLogger("shroudkeeper.worldname")


def resolve_info_file(root_dir: Path, prefix: str) -> Path | None:
    index_path = root_dir / f"{prefix}_info-index"

    if index_path.exists() and index_path.is_file():
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            latest = int(payload.get("latest"))
            if latest == 0:
                candidate = root_dir / f"{prefix}_info"
            else:
                candidate = root_dir / f"{prefix}_info-{latest}"

            if candidate.exists() and candidate.is_file():
                return candidate

            return _resolve_without_index(root_dir, prefix)
        except Exception:
            _logger.warning("Invalid _info-index for prefix: %s", prefix)
            return _resolve_without_index(root_dir, prefix)

    return _resolve_without_index(root_dir, prefix)


def _resolve_without_index(root_dir: Path, prefix: str) -> Path | None:
    base = root_dir / f"{prefix}_info"
    if base.exists() and base.is_file():
        return base

    highest: tuple[int, Path] | None = None
    pattern = f"{prefix}_info-"
    for entry in root_dir.glob(f"{prefix}_info-*"):
        if not entry.is_file():
            continue
        name = entry.name
        if not name.startswith(pattern):
            continue
        suffix = name[len(pattern) :]
        if not suffix.isdigit():
            continue
        value = int(suffix)
        if highest is None or value > highest[0]:
            highest = (value, entry)

    if highest is None:
        return None
    return highest[1]
