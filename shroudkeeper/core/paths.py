from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Shroudkeeper"


def get_app_data_dir() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        base_dir = Path.home() / ".config"

    app_data_dir = base_dir / APP_NAME
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir.resolve()


def get_logs_dir() -> Path:
    logs_dir = get_app_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir.resolve()


def get_backups_dir() -> Path:
    if os.name == "nt":
        userprofile = os.getenv("USERPROFILE")
        base_dir = Path(userprofile) if userprofile else Path.home()
        backups_dir = base_dir / "Saved Games"
    else:
        backups_dir = Path.home() / "Saved Games"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir.resolve()


def get_config_path() -> Path:
    return (get_app_data_dir() / "config.json").resolve()


def get_database_path() -> Path:
    app_data_dir = get_app_data_dir()
    legacy_path = (app_data_dir / "embervault.db").resolve()
    new_path = (app_data_dir / "shroudkeeper.db").resolve()
    if legacy_path.exists() and not new_path.exists():
        try:
            legacy_path.replace(new_path)
        except OSError:
            return legacy_path
    return new_path


def get_default_singleplayer_root() -> Path:
    if os.name == "nt":
        userprofile = os.getenv("USERPROFILE")
        base = Path(userprofile) if userprofile else Path.home()
        return (base / "Saved Games" / "enshrouded").resolve()
    return (Path.home() / "Saved Games" / "enshrouded").resolve()


def ensure_runtime_directories() -> None:
    get_app_data_dir()
    get_logs_dir()
    get_backups_dir()
