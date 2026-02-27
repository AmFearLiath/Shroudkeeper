from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.profiles.credentials import CredentialService
from core.profiles.models import Profile
from core.saves.models import SaveScanResult, SaveSlot
from core.saves.scan_worker import SaveScanWorker
from core.saves.scanner_service import SaveScannerService
from core.saves.world_slots import WORLD_SLOT_MAPPING
from core.server.server_models import ServerScanResult
from core.server.server_scan_worker import ServerScanWorker
from core.system.process_check import can_write_singleplayer_files, singleplayer_write_block_message
from core.transfers.transfer_models import TransferDirection, TransferPlan, TransferResult
from core.transfers.transfer_service import build_plan_server_to_sp, build_plan_sp_to_server, build_plan_sp_to_sp
from core.transfers.transfer_worker import TransferWorker
from i18n.i18n import get_i18n, tr
from storage.repositories import ProfileRepository
from ui.components.ev_badge import EVBadge
from ui.components.ev_page_header import EVPageHeader
from ui.widgets.password_dialog import PasswordDialog


class TransfersView(QWidget):
    def __init__(self, connection: sqlite3.Connection, config: AppConfig, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger
        self._config = config
        self._repo = ProfileRepository(connection)
        self._credential_service = CredentialService()

        self._scan_service = SaveScannerService(logger=logger)
        self._scan_thread: QThread | None = None
        self._scan_worker: SaveScanWorker | None = None

        self._server_scan_thread: QThread | None = None
        self._server_scan_worker: ServerScanWorker | None = None

        self._transfer_thread: QThread | None = None
        self._transfer_worker: TransferWorker | None = None

        self._source_slots: dict[int, SaveSlot] = {}
        self._scan_result: SaveScanResult | None = None
        self._server_result: ServerScanResult | None = None
        self._latest_roll: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._header = EVPageHeader()
        layout.addWidget(self._header)

        self._description = QLabel()
        self._description.setWordWrap(True)
        layout.addWidget(self._description)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        self._content = QWidget()
        self._content.setObjectName("TransfersContent")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        content_row.addWidget(self._content, 1)
        layout.addLayout(content_row, 1)

        source_target_row = QHBoxLayout()
        source_target_row.setContentsMargins(0, 0, 0, 0)
        source_target_row.setSpacing(12)

        self._source_card = QFrame()
        self._source_card.setObjectName("EVCard")
        self._source_card.setProperty("activeSource", "singleplayer")
        source_layout = QGridLayout(self._source_card)
        source_layout.setContentsMargins(16, 16, 16, 16)
        source_layout.setHorizontalSpacing(12)
        source_layout.setVerticalSpacing(10)
        source_layout.setRowStretch(99, 1)

        self._source_title = QLabel()
        self._source_title.setObjectName("cardTitle")
        source_layout.addWidget(self._source_title, 0, 0, 1, 2)

        self._source_type_label = QLabel()
        source_layout.addWidget(self._source_type_label, 1, 0)

        self._source_type_combo = QComboBox()
        self._source_type_combo.addItem("", "singleplayer")
        self._source_type_combo.addItem("", "server")
        source_layout.addWidget(self._source_type_combo, 1, 1)

        self._source_slot_label = QLabel()
        source_layout.addWidget(self._source_slot_label, 2, 0)

        self._source_slot_combo = QComboBox()
        source_layout.addWidget(self._source_slot_combo, 2, 1)

        self._source_server_profile_label = QLabel()
        source_layout.addWidget(self._source_server_profile_label, 3, 0)

        self._source_server_profile_combo = QComboBox()
        source_layout.addWidget(self._source_server_profile_combo, 3, 1)

        self._roll_label = QLabel()
        source_layout.addWidget(self._roll_label, 4, 0)

        roll_row = QHBoxLayout()
        roll_row.setContentsMargins(0, 0, 0, 0)
        roll_row.setSpacing(8)

        self._roll_combo = QComboBox()
        roll_row.addWidget(self._roll_combo, 1)

        self._roll_badge = EVBadge(tone="info", size="sm")
        roll_row.addWidget(self._roll_badge)

        source_layout.addLayout(roll_row, 4, 1)

        self._target_card = QFrame()
        self._target_card.setObjectName("EVCard")
        self._target_card.setProperty("activeTarget", "singleplayer")
        target_layout = QGridLayout(self._target_card)
        target_layout.setContentsMargins(16, 16, 16, 16)
        target_layout.setHorizontalSpacing(12)
        target_layout.setVerticalSpacing(10)
        target_layout.setRowStretch(99, 1)

        self._target_title = QLabel()
        self._target_title.setObjectName("cardTitle")
        target_layout.addWidget(self._target_title, 0, 0, 1, 2)

        self._target_type_label = QLabel()
        target_layout.addWidget(self._target_type_label, 1, 0)

        self._target_type_combo = QComboBox()
        self._target_type_combo.addItem("", "singleplayer")
        self._target_type_combo.addItem("", "server")
        target_layout.addWidget(self._target_type_combo, 1, 1)

        self._target_slot_label = QLabel()
        target_layout.addWidget(self._target_slot_label, 2, 0)

        self._target_slot_combo = QComboBox()
        target_layout.addWidget(self._target_slot_combo, 2, 1)

        self._target_server_profile_label = QLabel()
        target_layout.addWidget(self._target_server_profile_label, 3, 0)

        self._target_server_profile_combo = QComboBox()
        target_layout.addWidget(self._target_server_profile_combo, 3, 1)

        source_target_row.addWidget(self._source_card, 1)
        source_target_row.addWidget(self._target_card, 1)
        content_layout.addLayout(source_target_row)

        self._server_profile_info = QLabel()
        self._server_profile_info.setObjectName("infoBar")
        self._server_profile_info.setVisible(False)
        content_layout.addWidget(self._server_profile_info)

        self._action_card = QFrame()
        self._action_card.setObjectName("EVCard")
        action_layout = QVBoxLayout(self._action_card)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(10)

        self._action_title = QLabel()
        self._action_title.setObjectName("cardTitle")
        action_layout.addWidget(self._action_title)

        self._confirm_overwrite_checkbox = QCheckBox()
        self._confirm_overwrite_checkbox.setChecked(True)
        action_layout.addWidget(self._confirm_overwrite_checkbox)

        self._start_button = QPushButton()
        self._start_button.setProperty("variant", "primary")
        self._start_button.setProperty("fullWidth", True)
        self._start_button.clicked.connect(self._on_start_transfer)
        action_layout.addWidget(self._start_button)

        self._safety_info = QLabel()
        self._safety_info.setObjectName("infoBar")
        self._safety_info.setWordWrap(True)
        self._safety_info.setVisible(False)
        action_layout.addWidget(self._safety_info)

        self._progress_section = QWidget()
        progress_layout = QVBoxLayout(self._progress_section)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")
        progress_layout.addWidget(self._status_label)

        action_layout.addWidget(self._progress_section)

        content_layout.addWidget(self._action_card)
        content_layout.addStretch(1)

        self._source_type_combo.currentIndexChanged.connect(self._update_source_target_state)
        self._target_type_combo.currentIndexChanged.connect(self._update_source_target_state)
        self._source_slot_combo.currentIndexChanged.connect(self._reload_roll_options)
        self._source_server_profile_combo.currentIndexChanged.connect(self._on_source_server_profile_changed)
        self._target_server_profile_combo.currentIndexChanged.connect(self._on_target_server_profile_changed)
        self._roll_combo.currentIndexChanged.connect(self._on_roll_selection_changed)
        self._target_slot_combo.currentIndexChanged.connect(self._update_start_button_state)
        self._confirm_overwrite_checkbox.toggled.connect(self._update_start_button_state)

        get_i18n().language_changed.connect(self.retranslate_ui)

        self.retranslate_ui()
        self._populate_target_slots()
        self._populate_profile_items()
        self._start_local_scan()
        self._update_source_target_state()

    def refresh_sources(self) -> None:
        self._populate_profile_items()
        self._server_result = None
        self._start_local_scan()
        if self._source_kind() == "server":
            self._ensure_server_scan_started()
        self._reload_roll_options()
        self._update_start_button_state()

    def _start_local_scan(self) -> None:
        if self._scan_thread is not None:
            return

        root = Path(self._config.get_singleplayer_root())
        self._set_busy_state(True)
        self._status_label.setText(tr("transfers.progress.preparing"))
        self._update_progress_section_visibility()

        thread = QThread(self)
        worker = SaveScanWorker(scanner=self._scan_service, root=root)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_local_scan_finished)
        worker.failed.connect(self._on_local_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_local_scan_closed)

        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_local_scan_finished(self, result: object) -> None:
        if not isinstance(result, SaveScanResult):
            return

        self._scan_result = result
        self._source_slots = {slot.slot_number: slot for slot in result.slots}
        self._populate_source_slots()
        self._reload_roll_options()

    def _on_local_scan_failed(self, message: str) -> None:
        self._status_label.setText(tr("transfers.status.scan_failed", error=message))
        self._update_progress_section_visibility()

    def _on_local_scan_closed(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self._set_busy_state(False)
        self._update_start_button_state()

    def _start_server_scan(self) -> None:
        if self._server_scan_thread is not None:
            return

        profile = self._selected_source_server_profile()
        if profile is None or profile.id is None:
            self._status_label.setText(tr("transfers.error.no_active_profile"))
            self._update_start_button_state()
            return

        password = self._credential_service.get_password(profile.id, profile.username)
        if not password:
            password_dialog = PasswordDialog(profile_name=profile.name, parent=self)
            if password_dialog.exec() != PasswordDialog.DialogCode.Accepted:
                return

            password = password_dialog.password()
            if password_dialog.remember_password() and password:
                self._credential_service.set_password(profile.id, profile.username, password)

        self._set_busy_state(True)
        self._status_label.setText(tr("transfers.status.server_scanning"))
        self._update_progress_section_visibility()

        thread = QThread(self)
        worker = ServerScanWorker(profile=profile, password=password, logger=self._logger)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_server_scan_finished)
        worker.failed.connect(self._on_server_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_server_scan_closed)

        self._server_scan_thread = thread
        self._server_scan_worker = worker
        thread.start()

    def _on_server_scan_finished(self, result: object) -> None:
        if not isinstance(result, ServerScanResult):
            return

        self._server_result = result
        self._reload_roll_options()
        self._status_label.setText(tr("transfers.status.server_scan_finished"))
        self._update_progress_section_visibility()

    def _on_server_scan_failed(self, message: str) -> None:
        self._status_label.setText(tr("transfers.status.server_scan_failed", error=message))
        self._update_progress_section_visibility()

    def _on_server_scan_closed(self) -> None:
        self._server_scan_thread = None
        self._server_scan_worker = None
        self._set_busy_state(False)
        self._update_start_button_state()

    def _on_start_transfer(self) -> None:
        if self._transfer_thread is not None:
            return

        plan = self._build_plan()
        if plan is None:
            self._status_label.setText(tr("transfers.error.no_selection"))
            self._update_start_button_state()
            return

        if self._writes_local(plan.direction) and not can_write_singleplayer_files():
            self._status_label.setText(singleplayer_write_block_message())
            self._update_start_button_state()
            return

        if plan.direction == TransferDirection.SP_TO_SERVER:
            confirmed = QMessageBox.question(
                self,
                tr("transfers.warning.server_must_be_stopped.title"),
                tr("transfers.warning.server_must_be_stopped.text"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                return

        overwrite_file = self._target_overwrite_file(plan)
        if overwrite_file is not None and self._confirm_overwrite_checkbox.isChecked():
            confirmed = QMessageBox.question(
                self,
                tr("transfers.confirm.overwrite.title"),
                tr("transfers.confirm.overwrite.text", file=overwrite_file),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                return

        profile: Profile | None = None
        password: str | None = None

        if plan.direction in {TransferDirection.SP_TO_SERVER, TransferDirection.SERVER_TO_SP}:
            if plan.direction == TransferDirection.SP_TO_SERVER:
                profile = self._selected_target_server_profile()
            else:
                profile = self._selected_source_server_profile()
            if profile is None or profile.id is None:
                self._status_label.setText(tr("transfers.error.no_active_profile"))
                self._update_start_button_state()
                return

            password = self._credential_service.get_password(profile.id, profile.username)
            if not password:
                password_dialog = PasswordDialog(profile_name=profile.name, parent=self)
                if password_dialog.exec() != PasswordDialog.DialogCode.Accepted:
                    return

                password = password_dialog.password()
                if password_dialog.remember_password() and password:
                    self._credential_service.set_password(profile.id, profile.username, password)

        self._set_busy_state(True)
        self._progress_bar.setValue(0)
        self._status_label.setText(tr("transfers.progress.preparing"))
        self._update_progress_section_visibility()

        thread = QThread(self)
        worker = TransferWorker(plan=plan, logger=self._logger, profile=profile, password=password)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_transfer_progress)
        worker.success.connect(self._on_transfer_success)
        worker.error.connect(self._on_transfer_error)
        worker.success.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_transfer_closed)

        self._transfer_thread = thread
        self._transfer_worker = worker
        thread.start()

    def _on_transfer_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(max(0, min(100, percent)))
        self._status_label.setText(message)
        self._update_progress_section_visibility()

    def _on_transfer_success(self, result: object) -> None:
        if not isinstance(result, TransferResult):
            return

        self._logger.info("Transfer success files=%s bytes=%s", result.files_copied, result.bytes_copied)
        self._status_label.setText(tr("transfers.status.finished"))
        self._update_progress_section_visibility()
        QMessageBox.information(
            self,
            tr("transfers.success.title"),
            tr("transfers.success.text", files=result.files_copied, bytes=result.bytes_copied),
        )

        self._start_local_scan()

    def _on_transfer_error(self, message: str) -> None:
        self._logger.error("Transfer failed: %s", message)
        self._status_label.setText(tr("transfers.status.failed", error=message))
        self._update_progress_section_visibility()
        QMessageBox.critical(self, tr("common.error"), tr("transfers.status.failed", error=message))

    def _on_transfer_closed(self) -> None:
        self._transfer_thread = None
        self._transfer_worker = None
        self._set_busy_state(False)
        self._update_start_button_state()

    def _populate_source_slots(self) -> None:
        selected = self._source_slot_combo.currentData()

        self._source_slot_combo.blockSignals(True)
        self._source_slot_combo.clear()
        for slot_number in sorted(self._source_slots.keys()):
            slot = self._source_slots[slot_number]
            self._source_slot_combo.addItem(
                tr("transfers.slot_item", slot=slot_number, name=slot.display_name),
                slot_number,
            )

        if selected is not None:
            index = self._source_slot_combo.findData(selected)
            if index >= 0:
                self._source_slot_combo.setCurrentIndex(index)

        self._source_slot_combo.blockSignals(False)

    def _populate_target_slots(self) -> None:
        selected = self._target_slot_combo.currentData()

        self._target_slot_combo.blockSignals(True)
        self._target_slot_combo.clear()
        for slot_number in range(1, 11):
            label = tr("transfers.target_slot_item", slot=slot_number, world_hex=WORLD_SLOT_MAPPING[slot_number])
            self._target_slot_combo.addItem(label, slot_number)

        if selected is not None:
            index = self._target_slot_combo.findData(selected)
            if index >= 0:
                self._target_slot_combo.setCurrentIndex(index)

        self._target_slot_combo.blockSignals(False)

    def _reload_roll_options(self) -> None:
        selected_roll = self._roll_combo.currentData()

        self._roll_combo.blockSignals(True)
        self._roll_combo.clear()

        existing_rolls: set[int] = set()
        self._latest_roll = None

        if self._source_kind() == "singleplayer":
            source_slot = self._selected_source_slot()
            if source_slot is not None:
                existing_rolls = {roll.roll_index for roll in source_slot.rolls if roll.exists}
                self._latest_roll = source_slot.latest if source_slot.latest in existing_rolls else None
        elif self._server_result is not None:
            existing_rolls = {roll.roll_index for roll in self._server_result.rolls if roll.exists}
            self._latest_roll = self._server_result.latest if self._server_result.latest in existing_rolls else None

        if self._latest_roll is not None:
            self._roll_combo.addItem(tr("transfers.roll.latest"), self._latest_roll)

        for roll_index in range(0, 10):
            self._roll_combo.addItem(tr("dashboard.roll_label", roll=roll_index), roll_index)

        model = self._roll_combo.model()
        if isinstance(model, QStandardItemModel):
            for index in range(self._roll_combo.count()):
                data = self._roll_combo.itemData(index)
                item = model.item(index)
                if item is None:
                    continue

                if self._latest_roll is not None and index == 0:
                    item.setEnabled(True)
                elif isinstance(data, int):
                    item.setEnabled(data in existing_rolls)

        target_index = 0
        if selected_roll is not None:
            found = self._roll_combo.findData(selected_roll)
            if found >= 0:
                target_index = found
            elif self._latest_roll is not None:
                latest_index = self._roll_combo.findData(self._latest_roll)
                if latest_index >= 0:
                    target_index = latest_index

        self._roll_combo.setCurrentIndex(target_index if self._roll_combo.count() > 0 else -1)
        self._roll_combo.blockSignals(False)
        self._update_roll_badge()
        self._update_start_button_state()

    def _build_plan(self) -> TransferPlan | None:
        selected_roll = self._roll_combo.currentData()
        if not isinstance(selected_roll, int):
            return None

        source_is_sp = self._source_kind() == "singleplayer"
        target_is_sp = self._target_kind() == "singleplayer"

        if source_is_sp and target_is_sp:
            source_slot = self._selected_source_slot()
            target_slot = self._selected_target_slot_number()
            if source_slot is None or target_slot is None:
                return None
            return build_plan_sp_to_sp(source_slot=source_slot, target_slot=target_slot, roll_index=selected_roll)

        if source_is_sp and not target_is_sp:
            source_slot = self._selected_source_slot()
            profile = self._selected_target_server_profile()
            if source_slot is None or profile is None:
                return None
            return build_plan_sp_to_server(
                source_slot=source_slot,
                roll_index=selected_roll,
                server_root=profile.remote_path,
            )

        if not source_is_sp and target_is_sp:
            target_slot = self._selected_target_slot_number()
            profile = self._selected_source_server_profile()
            if target_slot is None or profile is None:
                return None
            local_root = Path(self._config.get_singleplayer_root())
            return build_plan_server_to_sp(
                target_slot=target_slot,
                roll_index=selected_roll,
                local_root=local_root,
                server_root=profile.remote_path,
            )

        return None

    def _writes_local(self, direction: TransferDirection) -> bool:
        return direction in {TransferDirection.SP_TO_SP, TransferDirection.SERVER_TO_SP}

    def _target_overwrite_file(self, plan: TransferPlan) -> str | None:
        if len(plan.files) == 0:
            return None

        _src_name, dst_name = plan.files[0]

        if plan.direction in {TransferDirection.SP_TO_SP, TransferDirection.SERVER_TO_SP}:
            target_root = Path(plan.target_root)
            target_file = target_root / dst_name
            return dst_name if target_file.exists() else None

        if plan.direction == TransferDirection.SP_TO_SERVER:
            if self._server_result is None:
                return dst_name

            for roll in self._server_result.rolls:
                if roll.file_name == dst_name and roll.exists:
                    return dst_name

            return None

        return None

    def _selected_source_server_profile(self) -> Profile | None:
        profile_id = self._source_server_profile_combo.currentData()
        if not isinstance(profile_id, int):
            return None
        return self._repo.get_profile(profile_id)

    def _selected_target_server_profile(self) -> Profile | None:
        profile_id = self._target_server_profile_combo.currentData()
        if not isinstance(profile_id, int):
            return None
        return self._repo.get_profile(profile_id)

    def _populate_profile_items(self) -> None:
        profiles = [profile for profile in self._repo.list_profiles() if profile.id is not None]

        self._source_server_profile_combo.blockSignals(True)
        self._target_server_profile_combo.blockSignals(True)
        self._source_server_profile_combo.clear()
        self._target_server_profile_combo.clear()

        for profile in profiles:
            self._source_server_profile_combo.addItem(profile.name, profile.id)
            self._target_server_profile_combo.addItem(profile.name, profile.id)

        if self._source_server_profile_combo.count() > 0:
            self._source_server_profile_combo.setCurrentIndex(0)
        if self._target_server_profile_combo.count() > 0:
            self._target_server_profile_combo.setCurrentIndex(0)

        self._source_server_profile_combo.blockSignals(False)
        self._target_server_profile_combo.blockSignals(False)

    def _on_source_server_profile_changed(self) -> None:
        self._server_result = None
        if self._source_kind() == "server":
            self._ensure_server_scan_started()
        self._reload_roll_options()
        self._update_server_profile_info()

    def _on_target_server_profile_changed(self) -> None:
        self._update_start_button_state()
        self._update_server_profile_info()

    def _selected_source_slot(self) -> SaveSlot | None:
        slot_number = self._source_slot_combo.currentData()
        if not isinstance(slot_number, int):
            return None
        return self._source_slots.get(slot_number)

    def _selected_target_slot_number(self) -> int | None:
        slot_number = self._target_slot_combo.currentData()
        if not isinstance(slot_number, int):
            return None
        return slot_number

    def _source_kind(self) -> str:
        value = str(self._source_type_combo.currentData() or "singleplayer")
        return value if value in {"singleplayer", "server"} else "singleplayer"

    def _target_kind(self) -> str:
        value = str(self._target_type_combo.currentData() or "singleplayer")
        return value if value in {"singleplayer", "server"} else "singleplayer"

    def _set_busy_state(self, busy: bool) -> None:
        controls_enabled = not busy
        self._source_type_combo.setEnabled(controls_enabled)
        self._target_type_combo.setEnabled(controls_enabled)
        self._source_slot_combo.setEnabled(controls_enabled and self._source_kind() == "singleplayer")
        self._source_server_profile_combo.setEnabled(controls_enabled and self._source_kind() == "server")
        self._roll_combo.setEnabled(controls_enabled)
        self._target_slot_combo.setEnabled(controls_enabled and self._target_kind() == "singleplayer")
        self._target_server_profile_combo.setEnabled(controls_enabled and self._target_kind() == "server")
        self._confirm_overwrite_checkbox.setEnabled(controls_enabled)
        self._start_button.setEnabled(controls_enabled)
        self._update_progress_section_visibility()

    def _refresh_active_card_states(self) -> None:
        self._source_card.setProperty(
            "activeSource",
            "singleplayer" if self._source_kind() == "singleplayer" else "server",
        )
        self._target_card.setProperty(
            "activeTarget",
            "singleplayer" if self._target_kind() == "singleplayer" else "server",
        )

        self._source_card.style().unpolish(self._source_card)
        self._source_card.style().polish(self._source_card)
        self._source_card.update()

        self._target_card.style().unpolish(self._target_card)
        self._target_card.style().polish(self._target_card)
        self._target_card.update()

    def _compute_safety_warning(self) -> str | None:
        source_kind = self._source_kind()
        target_kind = self._target_kind()

        if source_kind == "singleplayer" and target_kind == "singleplayer":
            source_slot = self._selected_source_slot()
            target_slot = self._selected_target_slot_number()
            if source_slot is not None and target_slot is not None and source_slot.slot_number == target_slot:
                return tr("transfers.warning.same_slot", slot=target_slot)

        if source_kind == "server":
            profile = self._selected_source_server_profile()
            if profile is None or profile.id is None:
                return tr("transfers.error.no_active_profile")

        if target_kind == "server":
            profile = self._selected_target_server_profile()
            if profile is None or profile.id is None:
                return tr("transfers.error.no_active_profile")

        if source_kind == "server" and self._server_result is None:
            return tr("transfers.warning.server_scan_required")

        plan = self._build_plan()
        if plan is not None and self._writes_local(plan.direction) and not can_write_singleplayer_files():
            return singleplayer_write_block_message()

        if self._roll_combo.currentData() is None:
            return tr("transfers.error.no_selection")

        return None

    def _update_safety_badge(self) -> None:
        warning_text = self._compute_safety_warning()
        if warning_text is None:
            self._safety_info.clear()
            self._safety_info.setVisible(False)
            return

        self._safety_info.setText(warning_text)
        self._safety_info.setVisible(True)

    def _update_roll_badge(self) -> None:
        selected_index = self._roll_combo.currentIndex()
        selected_roll = self._roll_combo.currentData()

        if not isinstance(selected_roll, int):
            self._roll_badge.setVisible(False)
            return

        if self._latest_roll is not None and selected_index == 0:
            self._roll_badge.setText(tr("transfers.roll.latest"))
            self._roll_badge.set_tone("info")
            self._roll_badge.setVisible(True)
            return

        self._roll_badge.setText(tr("dashboard.roll_label", roll=selected_roll))
        self._roll_badge.set_tone("neutral")
        self._roll_badge.setVisible(True)

    def _update_progress_section_visibility(self) -> None:
        is_busy = self._transfer_thread is not None or self._scan_thread is not None or self._server_scan_thread is not None
        self._progress_section.setVisible(is_busy)

    def _ensure_server_scan_started(self) -> None:
        if self._server_scan_thread is not None:
            if self._status_label.text().strip() == "":
                self._status_label.setText(tr("transfers.status.server_scanning"))
            return

        if self._selected_source_server_profile() is None:
            return

        self._status_label.setText(tr("transfers.status.server_scanning"))
        self._start_server_scan()

    def _update_source_target_state(self) -> None:
        source_is_sp = self._source_kind() == "singleplayer"
        target_is_sp = self._target_kind() == "singleplayer"

        if not source_is_sp and not target_is_sp:
            self._target_type_combo.blockSignals(True)
            target_index = self._target_type_combo.findData("singleplayer")
            self._target_type_combo.setCurrentIndex(target_index if target_index >= 0 else 0)
            self._target_type_combo.blockSignals(False)
            target_is_sp = True

        self._source_slot_combo.setEnabled(source_is_sp and self._transfer_thread is None)
        self._target_slot_combo.setEnabled(target_is_sp and self._transfer_thread is None)
        self._source_server_profile_label.setVisible(not source_is_sp)
        self._source_server_profile_combo.setVisible(not source_is_sp)
        self._target_server_profile_label.setVisible(not target_is_sp)
        self._target_server_profile_combo.setVisible(not target_is_sp)

        if not source_is_sp or not target_is_sp:
            self._populate_profile_items()
            self._ensure_server_scan_started()

        self._refresh_active_card_states()
        self._reload_roll_options()
        self._update_server_profile_info()
        self._update_start_button_state()

    def _update_server_profile_info(self) -> None:
        source_kind = self._source_kind()
        target_kind = self._target_kind()

        if source_kind == "server":
            profile = self._selected_source_server_profile()
            if profile is not None:
                self._server_profile_info.setText(
                    tr(
                        "transfers.server_profile_info.source",
                        name=profile.name,
                        protocol=profile.protocol.upper(),
                        host=profile.host,
                        port=profile.port,
                        remote_path=profile.remote_path,
                    )
                )
                self._server_profile_info.setVisible(True)
                return

        if target_kind == "server":
            profile = self._selected_target_server_profile()
            if profile is not None:
                self._server_profile_info.setText(
                    tr(
                        "transfers.server_profile_info.target",
                        name=profile.name,
                        protocol=profile.protocol.upper(),
                        host=profile.host,
                        port=profile.port,
                        remote_path=profile.remote_path,
                    )
                    + "\n"
                    + tr("transfers.warning.server_must_be_stopped.inline")
                )
                self._server_profile_info.setVisible(True)
                return

        self._server_profile_info.clear()
        self._server_profile_info.setVisible(False)

    def _update_start_button_state(self) -> None:
        enabled = self._transfer_thread is None and self._scan_thread is None and self._server_scan_thread is None

        if self._source_kind() == "server" and self._server_result is None:
            enabled = False

        if self._source_kind() == "singleplayer" and self._selected_source_slot() is None:
            enabled = False

        if self._target_kind() == "singleplayer" and self._selected_target_slot_number() is None:
            enabled = False

        if self._roll_combo.currentData() is None:
            enabled = False

        if self._source_kind() == "server" and self._target_kind() == "server":
            enabled = False

        if self._compute_safety_warning() is not None:
            enabled = False

        self._start_button.setEnabled(enabled)
        self._update_roll_badge()
        self._update_safety_badge()
        self._update_progress_section_visibility()

    def _on_roll_selection_changed(self) -> None:
        self._update_roll_badge()
        self._update_start_button_state()

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("transfers.title"))
        self._description.setText(tr("transfers.description"))

        self._source_title.setText(tr("transfers.source"))
        self._source_type_label.setText(tr("transfers.type"))
        self._source_server_profile_label.setText(tr("backups.server.profile"))
        source_sp_index = self._source_type_combo.findData("singleplayer")
        source_srv_index = self._source_type_combo.findData("server")
        if source_sp_index >= 0:
            self._source_type_combo.setItemText(source_sp_index, tr("transfers.source.singleplayer"))
        if source_srv_index >= 0:
            self._source_type_combo.setItemText(source_srv_index, tr("transfers.source.server"))
        self._source_slot_label.setText(tr("transfers.slot"))
        self._roll_label.setText(tr("transfers.roll"))

        self._target_title.setText(tr("transfers.target"))
        self._target_type_label.setText(tr("transfers.type"))
        self._target_server_profile_label.setText(tr("backups.server.profile"))
        target_sp_index = self._target_type_combo.findData("singleplayer")
        target_srv_index = self._target_type_combo.findData("server")
        if target_sp_index >= 0:
            self._target_type_combo.setItemText(target_sp_index, tr("transfers.target.singleplayer"))
        if target_srv_index >= 0:
            self._target_type_combo.setItemText(target_srv_index, tr("transfers.target.server"))
        self._target_slot_label.setText(tr("transfers.slot"))

        self._action_title.setText(tr("transfers.action"))
        self._confirm_overwrite_checkbox.setText(tr("transfers.confirm_overwrite"))
        self._start_button.setText(tr("transfers.start"))

        if self._status_label.text().strip() == "":
            self._status_label.setText(tr("transfers.status.idle"))

        self._populate_target_slots()
        self._populate_source_slots()
        self._reload_roll_options()
        self._refresh_active_card_states()
        self._update_server_profile_info()
        self._update_start_button_state()
