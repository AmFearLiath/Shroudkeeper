from __future__ import annotations

import os
from pathlib import Path
import shutil
import uuid

from core.saves.index_service import IndexFileService


def copy_file_atomic(src: Path, dst: Path) -> int:
    source = Path(src)
    target = Path(dst)

    if not source.exists() or not source.is_file():
        raise FileNotFoundError(str(source))

    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")

    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, target)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

    return int(target.stat().st_size)


def ensure_dir(path: Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def write_local_latest_index(index_path: Path, latest: int) -> None:
    index_service = IndexFileService()
    index_service.write_latest(Path(index_path), latest)
