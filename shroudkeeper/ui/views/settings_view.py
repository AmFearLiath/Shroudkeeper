from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.logging import LogEmitter
from i18n.i18n import get_i18n, tr
from ui.components.ev_page_header import EVPageHeader
from ui.widgets.log_console import LogConsole


class SettingsView(QWidget):
    language_selected = Signal(str)
    theme_selected = Signal(str)

    def __init__(
        self,
        current_language: str,
        current_theme: str,
        log_emitter: LogEmitter,
    ) -> None:
        super().__init__()

        self._language_codes = self._resolve_language_codes()
        self._theme_files = [
            "shroudkeeper",
            "dark_neon_orange",
            "dark_neon_green",
            "dark_neon_blue",
            "dark_neon_yellow",
            "light_dark_red",
            "light_dark_green",
            "light_dark_blue",
        ]

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self._header = EVPageHeader()
        main_layout.addWidget(self._header)

        self._description = QLabel()
        self._description.setWordWrap(True)
        main_layout.addWidget(self._description)

        self._general_card = QWidget()
        self._general_card.setObjectName("EVCard")
        general_layout = QVBoxLayout(self._general_card)
        general_layout.setContentsMargins(16, 16, 16, 16)
        general_layout.setSpacing(12)

        self._general_title = QLabel()
        self._general_title.setObjectName("cardTitle")
        general_layout.addWidget(self._general_title)

        language_row = QHBoxLayout()
        language_row.setSpacing(12)
        self._language_label = QLabel()
        self._language_combo = QComboBox()
        language_row.addWidget(self._language_label)
        language_row.addWidget(self._language_combo)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        self._theme_label = QLabel()
        self._theme_combo = QComboBox()
        theme_row.addWidget(self._theme_label)
        theme_row.addWidget(self._theme_combo)

        general_layout.addLayout(language_row)
        general_layout.addLayout(theme_row)

        main_layout.addWidget(self._general_card)

        self._log_card = QWidget()
        self._log_card.setObjectName("EVCard")
        log_layout = QVBoxLayout(self._log_card)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(10)

        self._log_title = QLabel()
        self._log_title.setObjectName("cardTitle")
        log_layout.addWidget(self._log_title)

        self._log_console = LogConsole(log_emitter)
        log_layout.addWidget(self._log_console)

        main_layout.addWidget(self._log_card, 1)

        self._apply_button = QPushButton()
        self._apply_button.setProperty("variant", "primary")
        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        action_row.addStretch(1)
        action_row.addWidget(self._apply_button)
        main_layout.addLayout(action_row)
        main_layout.addWidget(self._status_label)

        self._apply_button.clicked.connect(self._apply_changes)
        get_i18n().language_changed.connect(self.retranslate_ui)

        self._populate_language_items(current_language)
        self._populate_theme_items(current_theme)
        self.retranslate_ui()

    def _resolve_language_codes(self) -> list[str]:
        available = get_i18n().available_languages()
        preferred_order = [
            "de",
            "en",
            "ru",
            "fr",
            "it",
            "es",
            "pt",
            "pl",
            "bg",
            "cs",
            "tr",
            "zh",
            "ja",
            "vi",
        ]

        ordered = [code for code in preferred_order if code in available]
        extras = [code for code in available if code not in ordered]
        result = ordered + extras
        return result or ["de", "en"]

    def _populate_language_items(self, current_language: str) -> None:
        self._language_combo.clear()
        selected_index = 0

        for index, code in enumerate(self._language_codes):
            self._language_combo.addItem(tr(f"settings.language.{code}"), code)
            if code == current_language:
                selected_index = index

        self._language_combo.setCurrentIndex(selected_index)

    def _populate_theme_items(self, current_theme: str) -> None:
        normalized_current = current_theme.strip().lower()
        if normalized_current.endswith(".qss"):
            normalized_current = normalized_current[:-4]

        self._theme_combo.clear()
        selected_index = 0

        for index, theme_file in enumerate(self._theme_files):
            theme_key = theme_file
            self._theme_combo.addItem(tr(f"settings.theme.{theme_key}"), theme_file)
            if theme_file == normalized_current:
                selected_index = index

        self._theme_combo.setCurrentIndex(selected_index)

    def _apply_changes(self) -> None:
        language_code = str(self._language_combo.currentData())
        theme_file = str(self._theme_combo.currentData())

        self.language_selected.emit(language_code)
        self.theme_selected.emit(theme_file)
        self._status_label.setText(tr("settings.saved"))

    def retranslate_ui(self, _language: str | None = None) -> None:
        selected_language = str(self._language_combo.currentData() or self._language_codes[0])
        selected_theme = str(self._theme_combo.currentData() or self._theme_files[0])

        self._header.set_title(tr("settings.title"))
        self._description.setText(tr("settings.description"))
        self._general_title.setText(tr("settings.general_title"))
        self._log_title.setText(tr("settings.log_title"))
        self._language_label.setText(tr("settings.language.label"))
        self._theme_label.setText(tr("settings.theme.label"))
        self._apply_button.setText(tr("settings.apply"))

        self._populate_language_items(selected_language)
        self._populate_theme_items(selected_theme)
