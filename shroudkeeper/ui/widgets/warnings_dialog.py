from __future__ import annotations

from collections import Counter

from PySide6.QtWidgets import QDialog, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

from i18n.i18n import tr


class WarningsDialog(QDialog):
    def __init__(self, warnings: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._warnings = list(warnings)

        self.setObjectName("warningsDialog")
        self.setModal(True)
        self.setMinimumSize(700, 420)
        self.resize(760, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._warnings_list = QListWidget()
        layout.addWidget(self._warnings_list, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self._close_button = QPushButton()
        self._close_button.clicked.connect(self.accept)
        button_row.addWidget(self._close_button)
        layout.addLayout(button_row)

        self._populate()

    def _populate(self) -> None:
        self.setWindowTitle(tr("dashboard.warnings_modal.title"))
        self._close_button.setText(tr("common.close"))

        self._warnings_list.clear()

        grouped = Counter(self._warnings)
        if not grouped:
            self._warnings_list.addItem(tr("dashboard.warnings_badge.none"))
            return

        for message, count in grouped.items():
            if count > 1:
                self._warnings_list.addItem(tr("dashboard.warning.grouped_count", message=message, count=count))
            else:
                self._warnings_list.addItem(message)
