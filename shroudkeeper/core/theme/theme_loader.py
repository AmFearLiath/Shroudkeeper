from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.resources import get_themes_dir
from core.theme.theme_tokens import apply_tokens, get_theme_tokens
from i18n.i18n import tr


BASE_THEME_FILE = "base.qss"
DEFAULT_THEME = "shroudkeeper"
SUPPORTED_THEMES = {
    "shroudkeeper",
    "dark_neon_orange",
    "dark_neon_green",
    "dark_neon_blue",
    "dark_neon_yellow",
    "light_dark_red",
    "light_dark_green",
    "light_dark_blue",
}


def resolve_theme_name(theme_setting: str) -> str:
    normalized = theme_setting.strip()
    if normalized == "":
        return DEFAULT_THEME
    if normalized.lower().endswith(".qss"):
        normalized = normalized[:-4]
    theme_name = normalized.lower()
    if theme_name not in SUPPORTED_THEMES:
        return DEFAULT_THEME
    return theme_name


def _read_qss(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def apply_theme(application: QApplication, theme_setting: str, logger: logging.Logger) -> None:
    themes_dir = get_themes_dir()
    theme_name = resolve_theme_name(theme_setting)

    base_qss = _read_qss(themes_dir / BASE_THEME_FILE)
    theme_qss = _read_qss(themes_dir / f"{theme_name}.qss")

    if theme_qss.strip() == "":
        logger.warning(tr("startup.theme.missing", theme=theme_name))
        theme_name = DEFAULT_THEME
        theme_qss = _read_qss(themes_dir / f"{theme_name}.qss")

    combined = "\n\n".join(part for part in [base_qss, theme_qss] if part.strip() != "")
    if combined.strip() == "":
        application.setStyleSheet("")
        logger.warning(tr("startup.theme.missing", theme=theme_name))
        return

    tokens = get_theme_tokens(theme_name)
    themed_stylesheet = apply_tokens(combined, tokens)
    application.setStyleSheet(themed_stylesheet)
    logger.info(tr("startup.theme.loaded", theme=theme_name))
