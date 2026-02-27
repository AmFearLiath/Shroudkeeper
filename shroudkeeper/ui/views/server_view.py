from __future__ import annotations

import logging
import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.config import AppConfig
from i18n.i18n import get_i18n, tr
from ui.components.ev_page_header import EVPageHeader
from ui.views.profiles_view import ProfilesView


class ServerView(QWidget):
    profiles_changed = Signal()

    def __init__(self, connection: sqlite3.Connection, config: AppConfig, logger: logging.Logger) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._header = EVPageHeader()
        layout.addWidget(self._header)

        self._description = QLabel()
        self._description.setWordWrap(True)
        layout.addWidget(self._description)

        self._profiles_view = ProfilesView(connection=connection, config=config, logger=logger)
        self._profiles_view.profiles_changed.connect(self.profiles_changed.emit)
        layout.addWidget(self._profiles_view)

        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")
        layout.addWidget(self._status_label)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("server.title"))
        self._description.setText(tr("server.description"))
        if self._status_label.text().strip() == "":
            self._status_label.setText(tr("server.status.idle"))
