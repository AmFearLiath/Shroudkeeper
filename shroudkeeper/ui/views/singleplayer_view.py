from __future__ import annotations

import logging
import os
from pathlib import Path
import re

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.paths import get_default_singleplayer_root
from core.saves.models import SaveScanResult, SaveSlot
from core.saves.scan_worker import SaveScanWorker
from core.saves.scanner_service import SaveScannerService
from i18n.i18n import get_i18n, tr
from ui.components.ev_page_header import EVPageHeader
from ui.widgets.slot_details_dialog import SlotDetailsDialog
from ui.widgets.warnings_dialog import WarningsDialog


class SingleplayerView(QWidget):
    singleplayer_root_selected = Signal(str)

    def __init__(self, singleplayer_root: str, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger
        self._scan_root = Path(singleplayer_root)
        self._scanner = SaveScannerService(logger=logger)
        self._current_result: SaveScanResult | None = None
        self._slot_by_number: dict[int, SaveSlot] = {}
        self._slot_rows: list[SaveSlot] = []
        self._scan_thread: QThread | None = None
        self._scan_worker: SaveScanWorker | None = None
        self._initialized_scan = False
        self._warnings: list[str] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        self._header = EVPageHeader()

        self._header_hint = QLabel()
        self._header_hint.setObjectName("infoBar")
        self._header.add_action(self._header_hint)

        self._warnings_badge = QPushButton()
        self._warnings_badge.setProperty("variant", "secondary")
        self._warnings_badge.clicked.connect(self._open_warnings_modal)
        self._header.add_action(self._warnings_badge)

        root_layout.addWidget(self._header)

        self._singleplayer_card = QWidget()
        self._singleplayer_card.setObjectName("EVCard")
        singleplayer_layout = QVBoxLayout(self._singleplayer_card)
        singleplayer_layout.setContentsMargins(16, 16, 16, 16)
        singleplayer_layout.setSpacing(10)

        self._singleplayer_title = QLabel()
        self._singleplayer_title.setObjectName("cardTitle")
        singleplayer_layout.addWidget(self._singleplayer_title)

        self._singleplayer_root_label = QLabel()
        singleplayer_layout.addWidget(self._singleplayer_root_label)

        singleplayer_root_row = QHBoxLayout()
        singleplayer_root_row.setSpacing(12)

        self._singleplayer_root_edit = QLineEdit()
        self._singleplayer_root_edit.setReadOnly(True)
        self._singleplayer_root_edit.setText(str(self._scan_root))
        singleplayer_root_row.addWidget(self._singleplayer_root_edit, 1)

        self._singleplayer_browse_button = QPushButton()
        self._singleplayer_browse_button.clicked.connect(self._browse_singleplayer_root)
        singleplayer_root_row.addWidget(self._singleplayer_browse_button)

        self._singleplayer_reset_button = QPushButton()
        self._singleplayer_reset_button.clicked.connect(self._reset_singleplayer_root)
        singleplayer_root_row.addWidget(self._singleplayer_reset_button)

        singleplayer_layout.addLayout(singleplayer_root_row)

        singleplayer_action_row = QHBoxLayout()
        singleplayer_action_row.setSpacing(12)

        self._singleplayer_save_button = QPushButton()
        self._singleplayer_save_button.setProperty("variant", "primary")
        self._singleplayer_save_button.clicked.connect(self._apply_singleplayer_root)
        singleplayer_action_row.addWidget(self._singleplayer_save_button)

        self._scan_button = QPushButton()
        self._scan_button.setProperty("variant", "secondary")
        self._scan_button.clicked.connect(self.start_scan)
        singleplayer_action_row.addWidget(self._scan_button)

        singleplayer_layout.addLayout(singleplayer_action_row)

        self._singleplayer_status = QLabel()
        self._singleplayer_status.setObjectName("infoBar")
        singleplayer_layout.addWidget(self._singleplayer_status)

        self._slots_card = QWidget()
        self._slots_card.setObjectName("EVCard")
        slots_layout = QVBoxLayout(self._slots_card)
        slots_layout.setContentsMargins(16, 16, 16, 16)
        slots_layout.setSpacing(12)

        self._slots_card_title = QLabel()
        self._slots_card_title.setObjectName("cardTitle")
        slots_layout.addWidget(self._slots_card_title)

        self._slots_table = QTableWidget(0, 7)
        self._slots_table.setObjectName("EVTable")
        self._slots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._slots_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._slots_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._slots_table.setAlternatingRowColors(True)
        self._slots_table.verticalHeader().setVisible(False)
        self._slots_table.setSortingEnabled(False)
        self._slots_table.cellDoubleClicked.connect(self._on_table_row_double_clicked)

        header = self._slots_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self._no_savegames_label = QLabel()
        self._no_savegames_label.setObjectName("infoBar")
        self._no_savegames_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        slots_layout.addWidget(self._slots_table, 1)
        slots_layout.addWidget(self._no_savegames_label)
        root_layout.addWidget(self._slots_card, 1)
        root_layout.addWidget(self._singleplayer_card)

        self._build_slots_table()
        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

        QTimer.singleShot(0, self._trigger_initial_scan)

    def _trigger_initial_scan(self) -> None:
        if self._initialized_scan:
            return

        if not self.isVisible():
            QTimer.singleShot(250, self._trigger_initial_scan)
            return

        self._initialized_scan = True
        self._auto_detect_and_apply_root()
        self.start_scan()

    def _auto_detect_and_apply_root(self) -> None:
        discovered = self._discover_savegame_roots()
        if len(discovered) == 0:
            return

        scored_candidates = sorted(
            ((path, self._candidate_score(path)) for path in discovered),
            key=lambda item: item[1],
            reverse=True,
        )
        best_score = scored_candidates[0][1]
        has_detected_saves = best_score[0] > 0

        try:
            current = self._scan_root.expanduser().resolve()
        except Exception:
            current = self._scan_root

        current_score = self._candidate_score(current)

        if current in discovered and (not has_detected_saves or current_score >= best_score):
            self.set_scan_root(str(current))
            return

        preferred_candidates = [path for path, score in scored_candidates if score == best_score]

        if len(preferred_candidates) == 1:
            chosen = preferred_candidates[0]
            self.singleplayer_root_selected.emit(str(chosen))
            self.set_scan_root(str(chosen))
            self._singleplayer_status.setText(tr("singleplayer.auto_detect.selected", path=str(chosen)))
            return

        items = [str(path) for path in preferred_candidates]
        selected, accepted = QInputDialog.getItem(
            self,
            tr("singleplayer.auto_detect.title"),
            tr("singleplayer.auto_detect.prompt"),
            items,
            0,
            False,
        )
        if accepted and selected:
            chosen = Path(selected)
            self.singleplayer_root_selected.emit(str(chosen))
            self.set_scan_root(str(chosen))
            self._singleplayer_status.setText(tr("singleplayer.auto_detect.selected", path=str(chosen)))

    def _candidate_score(self, candidate: Path) -> tuple[int, int]:
        try:
            root = candidate.expanduser().resolve()
        except Exception:
            return (0, 0)

        if not root.exists() or not root.is_dir():
            return (0, 0)

        patterns = [
            re.compile(r"^[0-9a-fA-F]{8}(?:-[0-9])?$"),
            re.compile(r"^[0-9a-fA-F]{8}-index$"),
            re.compile(r"^[0-9a-fA-F]{8}_info(?:-[0-9]+)?$"),
            re.compile(r"^[0-9a-fA-F]{8}_info-index$"),
        ]

        hit_count = 0
        try:
            for child in root.iterdir():
                if not child.is_file():
                    continue
                if any(pattern.match(child.name) for pattern in patterns):
                    hit_count += 1
        except OSError:
            return (0, 0)

        return (1 if hit_count > 0 else 0, hit_count)

    def _discover_savegame_roots(self) -> list[Path]:
        candidates: list[Path] = []

        current_cfg = self._singleplayer_root_edit.text().strip()
        if current_cfg != "":
            candidates.append(Path(current_cfg))

        userprofile = os.getenv("USERPROFILE")
        if userprofile:
            candidates.append(Path(userprofile) / "Saved Games" / "enshrouded")

        steam_install_dir = os.getenv("STEAMINSTALLDIRECTORY")
        if steam_install_dir:
            candidates.extend((Path(steam_install_dir) / "userdata").glob("*/1203620/remote"))

        candidates.extend((Path(r"C:\Program Files (x86)\Steam\userdata")).glob("*/1203620/remote"))

        unique: dict[str, Path] = {}
        for candidate in candidates:
            try:
                normalized = candidate.expanduser().resolve()
            except Exception:
                continue
            if normalized.exists() and normalized.is_dir():
                unique[str(normalized).lower()] = normalized

        return sorted(unique.values(), key=lambda path: str(path).lower())

    def set_scan_root(self, root_path: str) -> None:
        self._scan_root = Path(root_path)
        self._singleplayer_root_edit.setText(str(self._scan_root))

    def _browse_singleplayer_root(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            tr("settings.browse_title"),
            self._singleplayer_root_edit.text().strip() or str(get_default_singleplayer_root()),
        )
        if selected_dir:
            self._singleplayer_root_edit.setText(selected_dir)

    def _reset_singleplayer_root(self) -> None:
        self._singleplayer_root_edit.setText(str(get_default_singleplayer_root()))

    def _apply_singleplayer_root(self) -> None:
        selected_root = self._singleplayer_root_edit.text().strip()
        if selected_root == "":
            return

        self.singleplayer_root_selected.emit(selected_root)
        self.set_scan_root(selected_root)
        self._singleplayer_status.setText(tr("settings.saved"))
        self.start_scan()

    def start_scan(self) -> None:
        if self._scan_thread is not None:
            return

        self._scan_button.setEnabled(False)

        thread = QThread(self)
        worker = SaveScanWorker(scanner=self._scanner, root=self._scan_root)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_thread_closed)

        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_scan_thread_closed(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self._scan_button.setEnabled(True)

    def _on_scan_finished(self, result: object) -> None:
        if not isinstance(result, SaveScanResult):
            return

        self._current_result = result
        self._warnings = list(result.warnings)
        self._slot_by_number = {slot.slot_number: slot for slot in result.slots}
        self._slot_rows = sorted(result.slots, key=lambda slot: slot.slot_number)
        self._refresh_slots_table()
        self._update_warnings_badge()

        if len(self._warnings) > 0:
            self._logger.info(tr("dashboard.scan.finished_with_warnings", count=len(self._warnings)))

    def _on_scan_failed(self, error_message: str) -> None:
        self._logger.error("Save scan failed: %s", error_message)
        self._warnings = [tr("dashboard.scan.failed", error=error_message)]
        self._update_warnings_badge()

    def _build_slots_table(self) -> None:
        self._refresh_slots_table()

    def _build_actions_widget(self, slot_number: int) -> QWidget:
        container = QWidget()
        container.setProperty("isEmpty", True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        details_button = QPushButton()
        details_button.setObjectName("detailsButton")
        details_button.clicked.connect(lambda _checked=False, value=slot_number: self._open_slot_details(value))
        layout.addWidget(details_button)

        open_folder_button = QPushButton()
        open_folder_button.setObjectName("openFolderButton")
        open_folder_button.clicked.connect(lambda _checked=False, value=slot_number: self._open_slot_folder(value))
        layout.addWidget(open_folder_button)

        copy_world_id_button = QPushButton()
        copy_world_id_button.setObjectName("copyIdButton")
        copy_world_id_button.clicked.connect(lambda _checked=False, value=slot_number: self._copy_slot_world_id(value))
        layout.addWidget(copy_world_id_button)

        self._set_actions_widget_texts(container)

        return container

    def _set_actions_widget_texts(self, action_widget: QWidget) -> None:
        details_button = action_widget.findChild(QPushButton, "detailsButton")
        open_folder_button = action_widget.findChild(QPushButton, "openFolderButton")
        copy_id_button = action_widget.findChild(QPushButton, "copyIdButton")

        if details_button is not None:
            details_button.setText(tr("dashboard.action.details"))
        if open_folder_button is not None:
            open_folder_button.setText(tr("dashboard.action.open_folder"))
        if copy_id_button is not None:
            copy_id_button.setText(tr("dashboard.action.copy_world_id"))

    def _refresh_slots_table(self) -> None:
        if not self._slot_rows:
            self._slots_table.setRowCount(0)
            self._slots_table.hide()
            self._no_savegames_label.show()
            return

        self._slots_table.show()
        self._no_savegames_label.hide()

        self._slots_table.setRowCount(len(self._slot_rows))
        for row, slot in enumerate(self._slot_rows):
            slot_number = slot.slot_number

            values = [
                str(slot.slot_number),
                slot.display_name,
                slot.world_id_hex,
                self._format_latest(slot.latest),
                self._format_datetime(slot.last_modified),
                self._format_size(slot.total_size_bytes),
            ]

            for column, value in enumerate(values):
                item = self._slots_table.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    self._slots_table.setItem(row, column, item)

                item.setText(value)
                item.setData(Qt.ItemDataRole.UserRole, slot_number)
                if column == 1:
                    item.setToolTip(self._world_name_source_tooltip(slot.world_name_source))

            action_widget = self._slots_table.cellWidget(row, 6)
            if action_widget is None:
                action_widget = self._build_actions_widget(slot_number)
                self._slots_table.setCellWidget(row, 6, action_widget)

    def _world_name_source_tooltip(self, source: str) -> str:
        if source == "mapping":
            return tr("dashboard.world_name.source.mapping")
        if source == "info":
            return tr("dashboard.world_name.source.info")
        return tr("dashboard.world_name.source.fallback")

    def _open_slot_details(self, slot_number: int) -> None:
        slot = self._slot_by_number.get(slot_number)
        if slot is None:
            return

        dialog = SlotDetailsDialog(slot=slot, logger=self._logger, parent=self)
        dialog.exec()
        if dialog.rollback_applied():
            self.start_scan()

    def _open_slot_folder(self, slot_number: int) -> None:
        slot = self._slot_by_number.get(slot_number)
        if slot is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(slot.root_dir)))

    def _copy_slot_world_id(self, slot_number: int) -> None:
        slot = self._slot_by_number.get(slot_number)
        if slot is None:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(slot.world_id_hex)
            self._logger.info(tr("dashboard.action.copied_world_id"))

    def _on_table_row_double_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._slot_rows):
            return
        self._open_slot_details(self._slot_rows[row].slot_number)

    def _open_warnings_modal(self) -> None:
        dialog = WarningsDialog(warnings=self._warnings, parent=self)
        dialog.exec()

    def _update_warnings_badge(self) -> None:
        warning_count = len(self._warnings)
        if warning_count == 0:
            self._warnings_badge.setText(tr("dashboard.warnings_badge.none"))
            self._warnings_badge.setProperty("alert", False)
        else:
            self._warnings_badge.setText(tr("dashboard.warnings_badge.some", count=warning_count))
            self._warnings_badge.setProperty("alert", True)

        self._warnings_badge.style().unpolish(self._warnings_badge)
        self._warnings_badge.style().polish(self._warnings_badge)
        self._warnings_badge.update()

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("nav.singleplayer"))
        self._singleplayer_title.setText(tr("singleplayer.settings.title"))
        self._singleplayer_root_label.setText(tr("settings.singleplayer_root_label"))
        self._singleplayer_browse_button.setText(tr("settings.browse"))
        self._singleplayer_reset_button.setText(tr("settings.reset_default"))
        self._singleplayer_save_button.setText(tr("singleplayer.settings.save"))
        self._scan_button.setText(tr("singleplayer.scan"))
        self._header_hint.setText(tr("singleplayer.details.rollback_hint"))
        self._slots_card_title.setText(tr("dashboard.world_slots_title"))
        self._no_savegames_label.setText(tr("dashboard.no_savegames_found"))

        self._slots_table.setHorizontalHeaderLabels(
            [
                tr("dashboard.world_slots_table.slot"),
                tr("dashboard.world_slots_table.name"),
                tr("dashboard.world_slots_table.world_id"),
                tr("dashboard.world_slots_table.latest"),
                tr("dashboard.world_slots_table.last_modified"),
                tr("dashboard.world_slots_table.total_size"),
                tr("dashboard.world_slots_table.actions"),
            ]
        )

        for row in range(self._slots_table.rowCount()):
            action_widget = self._slots_table.cellWidget(row, 6)
            if action_widget is None:
                continue
            self._set_actions_widget_texts(action_widget)

        self._update_warnings_badge()
        self._refresh_slots_table()

    def _format_datetime(self, value) -> str:
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
            return tr("common.not_available")
        return tr("dashboard.roll_label", roll=latest)
