from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.paths import get_app_data_dir, get_backups_dir, get_config_path, get_default_singleplayer_root


class AppConfig:
    _SUPPORTED_THEMES = {
        "shroudkeeper",
        "dark_neon_orange",
        "dark_neon_green",
        "dark_neon_blue",
        "dark_neon_yellow",
        "light_dark_red",
        "light_dark_green",
        "light_dark_blue",
    }

    _DEFAULTS: dict[str, Any] = {
        "language": "de",
        "theme": "shroudkeeper",
        "last_opened_paths": [],
        "singleplayer_root": str(get_default_singleplayer_root()),
        "backup_root_dir": str(get_backups_dir()),
        "backup_zip_enabled": True,
        "backup_keep_uncompressed": False,
        "active_profile_id": None,
        "profile_connection_status": {},
    }

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or get_config_path()
        self._data: dict[str, Any] = {}
        self._load_or_create()

    def _load_or_create(self) -> None:
        if not self._config_path.exists():
            self._data = dict(self._DEFAULTS)
            self.save()
            return

        try:
            content = self._config_path.read_text(encoding="utf-8")
            loaded = json.loads(content)
            if not isinstance(loaded, dict):
                loaded = {}
        except (json.JSONDecodeError, OSError):
            loaded = {}

        self._data = dict(self._DEFAULTS)
        self._data.update(loaded)

        theme_value = str(self._data.get("theme", self._DEFAULTS["theme"])).strip().lower()
        if theme_value.endswith(".qss"):
            theme_value = theme_value[:-4]
        if theme_value not in self._SUPPORTED_THEMES:
            theme_value = self._DEFAULTS["theme"]
        self._data["theme"] = theme_value

        legacy_backup_default = (get_app_data_dir() / "Backups").resolve()
        configured_backup_root = Path(str(self._data.get("backup_root_dir", ""))).expanduser()
        try:
            configured_backup_root = configured_backup_root.resolve()
        except OSError:
            configured_backup_root = configured_backup_root

        if str(configured_backup_root).lower() == str(legacy_backup_default).lower():
            self._data["backup_root_dir"] = str(get_backups_dir())

        self.save()

    def save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get_language(self) -> str:
        return str(self._data.get("language", self._DEFAULTS["language"]))

    def set_language(self, language: str) -> None:
        self._data["language"] = language
        self.save()

    def get_theme(self) -> str:
        return str(self._data.get("theme", self._DEFAULTS["theme"]))

    def set_theme(self, theme: str) -> None:
        self._data["theme"] = theme
        self.save()

    def get_last_opened_paths(self) -> list[str]:
        paths = self._data.get("last_opened_paths", self._DEFAULTS["last_opened_paths"])
        if isinstance(paths, list):
            return [str(item) for item in paths]
        return []

    def set_last_opened_paths(self, paths: list[str]) -> None:
        self._data["last_opened_paths"] = [str(item) for item in paths]
        self.save()

    def get_singleplayer_root(self) -> str:
        return str(self._data.get("singleplayer_root", self._DEFAULTS["singleplayer_root"]))

    def set_singleplayer_root(self, root_path: str) -> None:
        self._data["singleplayer_root"] = str(root_path)
        self.save()

    def get_backup_root_dir(self) -> str:
        return str(self._data.get("backup_root_dir", self._DEFAULTS["backup_root_dir"]))

    def set_backup_root_dir(self, root_path: str) -> None:
        self._data["backup_root_dir"] = str(root_path)
        self.save()

    def get_backup_zip_enabled(self) -> bool:
        return bool(self._data.get("backup_zip_enabled", self._DEFAULTS["backup_zip_enabled"]))

    def set_backup_zip_enabled(self, enabled: bool) -> None:
        self._data["backup_zip_enabled"] = bool(enabled)
        self.save()

    def get_backup_keep_uncompressed(self) -> bool:
        return bool(
            self._data.get("backup_keep_uncompressed", self._DEFAULTS["backup_keep_uncompressed"])
        )

    def set_backup_keep_uncompressed(self, enabled: bool) -> None:
        self._data["backup_keep_uncompressed"] = bool(enabled)
        self.save()

    def get_active_profile_id(self) -> int | None:
        value = self._data.get("active_profile_id", self._DEFAULTS["active_profile_id"])
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def set_active_profile_id(self, profile_id: int | None) -> None:
        self._data["active_profile_id"] = profile_id if profile_id is None else int(profile_id)
        self.save()

    def get_profile_connection_status(self) -> dict[int, bool]:
        raw = self._data.get("profile_connection_status", self._DEFAULTS["profile_connection_status"])
        if not isinstance(raw, dict):
            return {}

        result: dict[int, bool] = {}
        for key, value in raw.items():
            try:
                profile_id = int(key)
            except (TypeError, ValueError):
                continue
            result[profile_id] = bool(value)
        return result

    def set_profile_connection_ok(self, profile_id: int, ok: bool) -> None:
        status = self.get_profile_connection_status()
        status[int(profile_id)] = bool(ok)
        self._data["profile_connection_status"] = {str(pid): value for pid, value in status.items()}
        self.save()

    def remove_profile_connection_status(self, profile_id: int) -> None:
        status = self.get_profile_connection_status()
        status.pop(int(profile_id), None)
        self._data["profile_connection_status"] = {str(pid): value for pid, value in status.items()}
        self.save()
