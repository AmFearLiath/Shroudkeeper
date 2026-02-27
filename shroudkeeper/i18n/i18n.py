from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.resources import get_translations_dir


class I18nManager(QObject):
    language_changed = Signal(str)

    def __init__(self, default_language: str = "de", fallback_language: str = "en") -> None:
        super().__init__()
        self._default_language = default_language
        self._fallback_language = fallback_language
        self._current_language = default_language
        self._translations: dict[str, dict[str, str]] = {}

    @property
    def current_language(self) -> str:
        return self._current_language

    def load_translations(self) -> None:
        translations_dir = get_translations_dir()
        self._translations.clear()

        if not translations_dir.exists():
            return

        for file_path in sorted(translations_dir.glob("*.json")):
            language = file_path.stem
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    self._translations[language] = {
                        str(key): str(value) for key, value in payload.items()
                    }
            except (OSError, json.JSONDecodeError):
                continue

        if self._default_language not in self._translations and self._translations:
            self._default_language = next(iter(self._translations.keys()))

        if self._fallback_language not in self._translations:
            self._fallback_language = self._default_language

        if self._current_language not in self._translations:
            self._current_language = self._default_language

    def available_languages(self) -> list[str]:
        return sorted(self._translations.keys())

    def set_language(self, language: str, emit_signal: bool = True) -> None:
        if language not in self._translations:
            language = self._default_language

        if self._current_language == language:
            return

        self._current_language = language
        if emit_signal:
            self.language_changed.emit(language)

    def translate(self, key: str, **kwargs: object) -> str:
        current_map = self._translations.get(self._current_language, {})
        fallback_map = self._translations.get(self._fallback_language, {})
        default_map = self._translations.get(self._default_language, {})

        template = current_map.get(key) or fallback_map.get(key) or default_map.get(key) or key
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template


_i18n = I18nManager()


def initialize_i18n(language: str) -> None:
    _i18n.load_translations()
    _i18n.set_language(language, emit_signal=False)


def get_i18n() -> I18nManager:
    return _i18n


def tr(key: str, **kwargs: object) -> str:
    return _i18n.translate(key, **kwargs)
