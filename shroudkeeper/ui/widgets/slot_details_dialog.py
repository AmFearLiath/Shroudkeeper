from __future__ import annotations

from datetime import datetime
import logging

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QComboBox,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QLabel,
    QWidget,
    QHeaderView,
)

from core.saves.index_service import IndexFileService
from core.saves.models import SaveSlot
from core.system.process_check import can_write_singleplayer_files, singleplayer_write_block_message
from i18n.i18n import tr


class SlotDetailsDialog(QDialog):
    def __init__(self, slot: SaveSlot, logger: logging.Logger, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slot = slot
        self._logger = logger
        self._index_service = IndexFileService(logger=logger)
        self._rollback_applied = False
        self.setObjectName("slotDetailsDialog")
        self.setModal(True)
        self.setMinimumSize(900, 520)
        self.resize(1000, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setObjectName("viewHeadline")
        layout.addWidget(self._title_label)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)

        self._badge_world_id = QLabel()
        self._badge_world_id.setObjectName("badgeLabel")
        badge_row.addWidget(self._badge_world_id)

        self._badge_latest = QLabel()
        self._badge_latest.setObjectName("badgeLabel")
        badge_row.addWidget(self._badge_latest)

        self._badge_modified = QLabel()
        self._badge_modified.setObjectName("badgeLabel")
        badge_row.addWidget(self._badge_modified)

        self._badge_size = QLabel()
        self._badge_size.setObjectName("badgeLabel")
        badge_row.addWidget(self._badge_size)

        badge_row.addStretch(1)
        layout.addLayout(badge_row)

        self._rolls_table = QTableWidget(0, 4)
        self._rolls_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._rolls_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._rolls_table.setAlternatingRowColors(True)
        self._rolls_table.verticalHeader().setVisible(False)
        self._rolls_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._rolls_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._rolls_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._rolls_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._rolls_table, 1)

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

        tools_row = QHBoxLayout()
        tools_row.setSpacing(8)

        self._open_folder_button = QPushButton()
        self._open_folder_button.setObjectName("smallToolButton")
        self._open_folder_button.clicked.connect(self._open_folder)
        tools_row.addWidget(self._open_folder_button)

        self._copy_world_id_button = QPushButton()
        self._copy_world_id_button.setObjectName("smallToolButton")
        self._copy_world_id_button.clicked.connect(self._copy_world_id)
        tools_row.addWidget(self._copy_world_id_button)
        tools_row.addStretch(1)
        layout.addLayout(tools_row)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._close_button = QPushButton()
        self._close_button.clicked.connect(self.accept)
        button_row.addWidget(self._close_button)
        layout.addLayout(button_row)

        self._populate()

    def _populate(self) -> None:
        self._title_label.setText(
            tr(
                "dashboard.slot_details_modal_title",
                slot=self._slot.slot_number,
                name=self._slot.display_name,
            )
        )

        self._badge_world_id.setText(tr("dashboard.badge_world_id", value=self._slot.world_id_hex))
        self._badge_latest.setText(tr("dashboard.badge_latest", value=self._format_latest(self._slot.latest)))
        self._badge_modified.setText(
            tr("dashboard.badge_last_modified", value=self._format_datetime(self._slot.last_modified))
        )
        self._badge_size.setText(
            tr("dashboard.badge_total_size", value=self._format_size(self._slot.total_size_bytes))
        )

        self._rolls_table.setHorizontalHeaderLabels(
            [
                tr("dashboard.roll_table.roll"),
                tr("dashboard.roll_table.exists"),
                tr("dashboard.roll_table.modified"),
                tr("dashboard.roll_table.size"),
            ]
        )

        self._rolls_table.setRowCount(len(self._slot.rolls))
        for row_index, roll in enumerate(self._slot.rolls):
            self._rolls_table.setItem(row_index, 0, QTableWidgetItem(tr("dashboard.roll_label", roll=roll.roll_index)))
            self._rolls_table.setItem(row_index, 1, QTableWidgetItem(tr("common.yes") if roll.exists else tr("common.no")))
            self._rolls_table.setItem(row_index, 2, QTableWidgetItem(self._format_datetime(roll.modified_at)))
            self._rolls_table.setItem(row_index, 3, QTableWidgetItem(self._format_size(roll.size_bytes)))

        self._rollback_combo.clear()
        preferred_index = -1
        for roll in self._slot.rolls:
            if not roll.exists:
                continue
            self._rollback_combo.addItem(tr("dashboard.roll_label", roll=roll.roll_index), roll.roll_index)
            if self._slot.latest is not None and roll.roll_index == self._slot.latest:
                preferred_index = self._rollback_combo.count() - 1

        if preferred_index >= 0:
            self._rollback_combo.setCurrentIndex(preferred_index)
        self._rollback_button.setEnabled(self._rollback_combo.count() > 0)

        self._open_folder_button.setText(tr("dashboard.open_folder"))
        self._copy_world_id_button.setText(tr("dashboard.copy_world_id"))
        self._rollback_label.setText(tr("transfers.roll"))
        self._rollback_button.setText(tr("singleplayer.rollback.action"))
        self._close_button.setText(tr("common.close"))

    def _apply_rollback(self) -> None:
        roll_index = self._rollback_combo.currentData()
        if not isinstance(roll_index, int):
            return

        if not can_write_singleplayer_files():
            QMessageBox.warning(self, tr("common.error"), singleplayer_write_block_message())
            return

        confirmed = QMessageBox.question(
            self,
            tr("singleplayer.rollback.confirm.title"),
            tr("singleplayer.rollback.confirm.text", slot=self._slot.slot_number, roll=roll_index),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self._index_service.write_latest(self._slot.index_path, roll_index)
        self._rollback_applied = True
        QMessageBox.information(
            self,
            tr("common.ok"),
            tr("singleplayer.rollback.done", slot=self._slot.slot_number, roll=roll_index),
        )
        self.accept()

    def rollback_applied(self) -> bool:
        return self._rollback_applied

    def _open_folder(self) -> None:
        folder_url = QUrl.fromLocalFile(str(self._slot.root_dir))
        opened = QDesktopServices.openUrl(folder_url)
        if not opened:
            self._logger.warning("Failed to open folder: %s", self._slot.root_dir)
            QMessageBox.warning(self, tr("common.error"), tr("dashboard.open_folder_failed"))

    def _copy_world_id(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._slot.world_id_hex)
            QMessageBox.information(self, tr("common.ok"), tr("dashboard.copied_world_id"))

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return tr("common.not_available")
        return value.strftime("%Y-%m-%d %H:%M:%S")

    def _format_size(self, size_bytes: int | None) -> str:
        if size_bytes is None:
            return tr("common.not_available")
        if size_bytes < 1024:
            return tr("units.bytes", value=size_bytes)
        if size_bytes < 1024 * 1024:
            return tr("units.kib", value=f"{size_bytes / 1024:.1f}")
        return tr("units.mib", value=f"{size_bytes / (1024 * 1024):.2f}")

    def _format_latest(self, latest: int | None) -> str:
        if latest is None:
            return tr("dashboard.latest_unavailable")
        return tr("dashboard.roll_label", roll=latest)
