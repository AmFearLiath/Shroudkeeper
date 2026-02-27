from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QTextEdit, QVBoxLayout, QWidget

from core.logging import LogEmitter
from i18n.i18n import get_i18n, tr


class LogConsole(QWidget):
    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__()
        self._emitter = emitter

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._group = QGroupBox()
        group_layout = QVBoxLayout(self._group)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        group_layout.addWidget(self._text_edit)

        layout.addWidget(self._group)

        self._emitter.log_message.connect(self.append_log)
        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def append_log(self, message: str) -> None:
        self._text_edit.append(message)

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._group.setTitle(tr("dashboard.live_log_title"))
