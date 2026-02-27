from __future__ import annotations

import json
from pathlib import Path

from core.paths import get_app_data_dir
from core.resources import resource_path
from core.worldname.extractor import extract_world_name_from_info_file
from core.worldname.index_files import resolve_info_file


_SOURCE_MAPPING = "mapping"
_SOURCE_INFO = "info"
_SOURCE_FALLBACK = "fallback"


def get_world_name(prefix: str, root_dir: Path) -> str | None:
    name, _source = get_world_name_with_source(prefix, root_dir)
    return name


def get_world_name_with_source(prefix: str, root_dir: Path) -> tuple[str | None, str]:
    merged_mapping = _load_merged_mapping()

    mapped_name = merged_mapping.get(prefix)
    if mapped_name:
        return mapped_name, _SOURCE_MAPPING

    info_path = resolve_info_file(root_dir, prefix)
    if info_path is None:
        return None, _SOURCE_FALLBACK

    best_guess, _top_candidates = extract_world_name_from_info_file(info_path)
    if best_guess:
        return best_guess, _SOURCE_INFO

    return None, _SOURCE_FALLBACK


def _load_merged_mapping() -> dict[str, str]:
    default_mapping = _load_mapping_file(resource_path("assets/worldname-mapping.json"))
    user_mapping = _load_mapping_file(get_app_data_dir() / "worldname-mapping.json")

    merged = dict(default_mapping)
    merged.update(user_mapping)
    return merged


def _load_mapping_file(path: Path) -> dict[str, str]:
    try:
        if not path.exists() or not path.is_file():
            return {}

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}

        result: dict[str, str] = {}
        for key, value in payload.items():
            if isinstance(key, str) and isinstance(value, str):
                normalized_key = key.strip().lower()
                normalized_value = value.strip()
                if normalized_key and normalized_value:
                    result[normalized_key] = normalized_value
        return result
    except Exception:
        return {}
