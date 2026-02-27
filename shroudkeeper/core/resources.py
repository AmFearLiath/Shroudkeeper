from __future__ import annotations

import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = _project_root()

    return (base_path / relative_path).resolve()


def get_schema_path() -> Path:
    return resource_path("storage/schema.sql")


def get_themes_dir() -> Path:
    return resource_path("assets/themes")


def get_translations_dir() -> Path:
    return resource_path("i18n/translations")


def get_icons_dir() -> Path:
    return resource_path("assets/icons")


def read_text_resource(relative_path: str, encoding: str = "utf-8") -> str:
    path = resource_path(relative_path)
    return path.read_text(encoding=encoding)
