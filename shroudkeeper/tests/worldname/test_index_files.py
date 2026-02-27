from __future__ import annotations

import json
from pathlib import Path

from core.worldname.index_files import resolve_info_file


def test_resolve_info_file_latest_zero(tmp_path: Path) -> None:
    prefix = "abc123"
    base_info = tmp_path / f"{prefix}_info"
    base_info.write_bytes(b"x")
    (tmp_path / f"{prefix}_info-index").write_text(json.dumps({"latest": 0}), encoding="utf-8")

    result = resolve_info_file(tmp_path, prefix)
    assert result == base_info


def test_resolve_info_file_latest_positive(tmp_path: Path) -> None:
    prefix = "abc123"
    rotated = tmp_path / f"{prefix}_info-2"
    rotated.write_bytes(b"x")
    (tmp_path / f"{prefix}_info-index").write_text(json.dumps({"latest": 2}), encoding="utf-8")

    result = resolve_info_file(tmp_path, prefix)
    assert result == rotated
