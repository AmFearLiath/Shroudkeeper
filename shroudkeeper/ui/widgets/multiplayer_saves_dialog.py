from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from core.server.server_models import ServerScanResult
from i18n.i18n import tr


class MultiplayerSavesDialog(QDialog):
    def __init__(
        self,
        profile_name: str,
        result: ServerScanResult,
        rollback_handler: Callable[[int], tuple[bool, str, ServerScanResult | None]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._profile_name = profile_name
        self._result = result
        self._rollback_handler = rollback_handler

        self.setModal(True)
        self.setMinimumSize(920, 520)
        self.resize(980, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setObjectName("viewHeadline")
        layout.addWidget(self._title)

        self._summary = QLabel()
        self._summary.setObjectName("infoBar")
        layout.addWidget(self._summary)

        self._table = QTableWidget(0, 5)
        self._table.setObjectName("EVTable")
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table, 1)

        rollback_row = QHBoxLayout()
        rollback_row.setSpacing(8)
        self._rollback_label = QLabel()
        rollback_row.addWidget(self._rollback_label)
        self._rollback_combo = QComboBox()
        rollback_row.addWidget(self._rollback_combo, 1)
        self._rollback_button = QPushButton()
        self._rollback_button.setProperty("variant", "danger")
        self._rollback_button.clicked.connect(self._apply_rollback)
        rollback_row.addWidget(self._rollback_button)
        layout.addLayout(rollback_row)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._close_button = QPushButton(tr("common.close"))
        self._close_button.clicked.connect(self.accept)
        buttons.addWidget(self._close_button)
        layout.addLayout(buttons)

        self._populate()

    def _populate(self) -> None:
        self.setWindowTitle(tr("multiplayer.details.title", profile=self._profile_name))
        self._title.setText(tr("multiplayer.details.title", profile=self._profile_name))

        latest_text = (
            tr("dashboard.roll_label", roll=self._result.latest)
            if self._result.latest is not None
            else tr("common.not_available")
        )
        self._summary.setText(
            tr(
                "server.summary.result",
                world_id=self._result.world_id_hex,
                remote_root=self._result.remote_root,
                latest=latest_text,
                warnings=tr("server.summary.warnings", count=len(self._result.warnings)),
            )
        )

        self._table.setHorizontalHeaderLabels(
            [
                tr("server.table.roll"),
                tr("server.table.file"),
                tr("server.table.exists"),
                tr("server.table.modified"),
                tr("server.table.size"),
            ]
        )

        self._table.setRowCount(len(self._result.rolls))
        for row, roll in enumerate(self._result.rolls):
            values = [
                tr("server.roll_label", roll=roll.roll_index),
                roll.file_name,
                tr("common.yes") if roll.exists else tr("common.no"),
                roll.modified_at.strftime("%Y-%m-%d %H:%M:%S") if roll.modified_at else tr("common.not_available"),
                self._format_size(roll.size_bytes),
            ]
            for col, value in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(value))

        self._rollback_label.setText(tr("transfers.roll"))
        self._rollback_button.setText(tr("singleplayer.rollback.action"))
        self._populate_rollback_options()

    def _populate_rollback_options(self) -> None:
        self._rollback_combo.clear()

        preferred_index = -1
        for roll in self._result.rolls:
            if not roll.exists:
                continue
            self._rollback_combo.addItem(tr("dashboard.roll_label", roll=roll.roll_index), roll.roll_index)
            if self._result.latest is not None and roll.roll_index == self._result.latest:
                preferred_index = self._rollback_combo.count() - 1

        if preferred_index >= 0:
            self._rollback_combo.setCurrentIndex(preferred_index)

        rollback_available = self._rollback_handler is not None and self._rollback_combo.count() > 0
        self._rollback_combo.setEnabled(rollback_available)
        self._rollback_button.setEnabled(rollback_available)

    def _apply_rollback(self) -> None:
        if self._rollback_handler is None:
            return

        roll_index = self._rollback_combo.currentData()
        if not isinstance(roll_index, int):
            return

        confirmed = QMessageBox.question(
            self,
            tr("singleplayer.rollback.confirm.title"),
            tr("server.rollback.confirm.text", roll=roll_index),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        success, message, updated_result = self._rollback_handler(roll_index)
        if not success:
            QMessageBox.warning(self, tr("common.error"), message)
            return

        if updated_result is not None:
            self._result = updated_result
            self._populate()

        QMessageBox.information(self, tr("common.ok"), tr("server.rollback.done", roll=roll_index))

    def _format_size(self, size_bytes: int | None) -> str:
        if size_bytes is None:
            return tr("common.not_available")
        if size_bytes < 1024:
            return tr("units.bytes", value=size_bytes)
        if size_bytes < 1024 * 1024:
            return tr("units.kib", value=f"{size_bytes / 1024:.1f}")
        return tr("units.mib", value=f"{size_bytes / (1024 * 1024):.2f}")
