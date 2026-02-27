from __future__ import annotations

import logging
from pathlib import Path
import shutil
import sqlite3

from PySide6.QtCore import Qt, QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHeaderView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.backups.backup_index import list_backups
from core.backups.models import BackupEntry, BackupResult, BackupType
from core.backups.server_backup_worker import ServerBackupWorker
from core.backups.singleplayer_backup_worker import SingleplayerBackupWorker
from core.config import AppConfig
from core.profiles.credentials import CredentialService
from core.profiles.models import Profile
from core.saves.models import SaveScanResult, SaveSlot
from core.saves.scan_worker import SaveScanWorker
from core.saves.scanner_service import SaveScannerService
from i18n.i18n import get_i18n, tr
from storage.repositories import ProfileRepository
from ui.widgets.password_dialog import PasswordDialog


class BackupsView(QWidget):
    def __init__(self, connection: sqlite3.Connection, config: AppConfig, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger
        self._config = config
        self._repo = ProfileRepository(connection)
        self._credential_service = CredentialService()

        self._scan_service = SaveScannerService(logger=logger)
        self._scan_thread: QThread | None = None
        self._scan_worker: SaveScanWorker | None = None
        self._scan_result: SaveScanResult | None = None
        self._slots_by_number: dict[int, SaveSlot] = {}

        self._backup_thread: QThread | None = None
        self._backup_worker: SingleplayerBackupWorker | ServerBackupWorker | None = None

        self._backup_entries: list[BackupEntry] = []
        self._profiles: dict[int, Profile] = {}

        self._running_server_profile: Profile | None = None
        self._retry_server_requested = False
        self._retry_server_password: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(0)

        root_scroll = QScrollArea()
        root_scroll.setWidgetResizable(True)
        root_scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(root_scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        root_scroll.setWidget(content)

        self._headline = QLabel()
        self._headline.setObjectName("viewHeadline")
        content_layout.addWidget(self._headline)

        create_card = QFrame()
        create_card.setObjectName("backupCreateCard")
        create_layout = QVBoxLayout(create_card)
        create_layout.setContentsMargins(16, 16, 16, 16)
        create_layout.setSpacing(12)

        self._create_title = QLabel()
        self._create_title.setObjectName("cardTitle")
        create_layout.addWidget(self._create_title)

        self._create_tabs = QTabWidget()
        self._create_tabs.setObjectName("backupCreateTabs")
        create_layout.addWidget(self._create_tabs)

        singleplayer_tab = QWidget()
        singleplayer_layout = QVBoxLayout(singleplayer_tab)
        singleplayer_layout.setContentsMargins(0, 0, 0, 0)
        singleplayer_layout.setSpacing(10)

        self._slots_list = QListWidget()
        self._slots_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._slots_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._slots_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._slots_list.itemChanged.connect(self._on_slot_item_changed)
        singleplayer_layout.addWidget(self._slots_list)

        self._singleplayer_create_button = QPushButton()
        self._singleplayer_create_button.setObjectName("primaryButton")
        self._singleplayer_create_button.clicked.connect(self._start_singleplayer_backup)
        singleplayer_layout.addWidget(self._singleplayer_create_button)

        server_tab = QWidget()
        server_layout = QVBoxLayout(server_tab)
        server_layout.setContentsMargins(0, 0, 0, 0)
        server_layout.setSpacing(10)

        server_row = QHBoxLayout()
        server_row.setSpacing(8)
        self._server_profile_label = QLabel()
        server_row.addWidget(self._server_profile_label)
        self._server_profile_combo = QComboBox()
        self._server_profile_combo.currentIndexChanged.connect(self._update_create_buttons_state)
        server_row.addWidget(self._server_profile_combo, 1)
        server_layout.addLayout(server_row)
        server_layout.addStretch(1)

        self._server_create_button = QPushButton()
        self._server_create_button.setObjectName("primaryButton")
        self._server_create_button.clicked.connect(self._start_server_backup_from_selection)
        server_layout.addWidget(self._server_create_button)

        self._create_tabs.addTab(singleplayer_tab, "")
        self._create_tabs.addTab(server_tab, "")

        content_layout.addWidget(create_card)

        self._settings_card = QFrame()
        self._settings_card.setObjectName("EVCard")
        settings_layout = QVBoxLayout(self._settings_card)
        settings_layout.setContentsMargins(16, 16, 16, 16)
        settings_layout.setSpacing(10)

        self._settings_title = QLabel()
        self._settings_title.setObjectName("cardTitle")
        settings_layout.addWidget(self._settings_title)

        self._backup_root_label = QLabel()
        settings_layout.addWidget(self._backup_root_label)

        root_row = QHBoxLayout()
        root_row.setSpacing(12)
        self._backup_root_edit = QLineEdit()
        self._backup_root_edit.setReadOnly(True)
        self._backup_root_edit.setText(self._config.get_backup_root_dir())
        root_row.addWidget(self._backup_root_edit, 1)

        self._backup_browse_button = QPushButton()
        self._backup_browse_button.clicked.connect(self._browse_backup_root)
        root_row.addWidget(self._backup_browse_button)

        self._backup_reset_button = QPushButton()
        self._backup_reset_button.clicked.connect(self._reset_backup_root)
        root_row.addWidget(self._backup_reset_button)
        settings_layout.addLayout(root_row)

        self._backup_zip_enabled_checkbox = QCheckBox()
        self._backup_zip_enabled_checkbox.setChecked(self._config.get_backup_zip_enabled())
        settings_layout.addWidget(self._backup_zip_enabled_checkbox)

        self._backup_keep_uncompressed_checkbox = QCheckBox()
        self._backup_keep_uncompressed_checkbox.setChecked(self._config.get_backup_keep_uncompressed())
        settings_layout.addWidget(self._backup_keep_uncompressed_checkbox)

        self._settings_save_button = QPushButton()
        self._settings_save_button.setObjectName("primaryButton")
        self._settings_save_button.clicked.connect(self._save_backup_settings)
        settings_layout.addWidget(self._settings_save_button)

        content_layout.addWidget(self._settings_card)

        self._status_card = QFrame()
        self._status_card.setObjectName("backupStatusCard")
        status_layout = QVBoxLayout(self._status_card)
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(10)

        self._status_title = QLabel()
        self._status_title.setObjectName("cardTitle")
        status_layout.addWidget(self._status_title)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        status_layout.addWidget(self._progress_bar)

        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")
        status_layout.addWidget(self._status_label)

        self._cancel_button = QPushButton()
        self._cancel_button.setObjectName("smallToolButton")
        self._cancel_button.setVisible(False)
        status_layout.addWidget(self._cancel_button)

        content_layout.addWidget(self._status_card)

        list_card = QFrame()
        list_card.setObjectName("backupListCard")
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(10)

        list_header = QHBoxLayout()
        list_header.setSpacing(8)
        self._list_title = QLabel()
        self._list_title.setObjectName("cardTitle")
        list_header.addWidget(self._list_title, 1)

        self._list_refresh_button = QPushButton()
        self._list_refresh_button.setObjectName("smallToolButton")
        self._list_refresh_button.clicked.connect(self._refresh_backup_list)
        list_header.addWidget(self._list_refresh_button)
        list_layout.addLayout(list_header)

        self._backups_table = QTableWidget(0, 6)
        self._backups_table.setObjectName("backupsTable")
        self._backups_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._backups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._backups_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._backups_table.verticalHeader().setVisible(False)
        self._backups_table.setAlternatingRowColors(True)
        self._backups_table.setMinimumHeight(260)

        header = self._backups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        list_layout.addWidget(self._backups_table)

        self._no_backups_label = QLabel()
        self._no_backups_label.setObjectName("infoBar")
        self._no_backups_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        list_layout.addWidget(self._no_backups_label)

        content_layout.addWidget(list_card)
        content_layout.addStretch(1)

        get_i18n().language_changed.connect(self.retranslate_ui)

        self._reload_profiles()
        self._start_local_scan()
        self._refresh_backup_list()
        self.retranslate_ui()
        self._set_status_card_visible(False)

    def refresh_sources(self) -> None:
        self._backup_root_edit.setText(self._config.get_backup_root_dir())
        self._backup_zip_enabled_checkbox.setChecked(self._config.get_backup_zip_enabled())
        self._backup_keep_uncompressed_checkbox.setChecked(self._config.get_backup_keep_uncompressed())
        self._reload_profiles()
        self._start_local_scan()
        self._refresh_backup_list()

    def _start_local_scan(self) -> None:
        if self._scan_thread is not None:
            return

        root = Path(self._config.get_singleplayer_root())

        thread = QThread(self)
        worker = SaveScanWorker(scanner=self._scan_service, root=root)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_closed)

        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_scan_finished(self, result: object) -> None:
        if not isinstance(result, SaveScanResult):
            return

        self._scan_result = result
        self._slots_by_number = {slot.slot_number: slot for slot in result.slots}
        self._populate_slot_list()

    def _on_scan_failed(self, message: str) -> None:
        self._status_label.setText(tr("backups.status.scan_failed", error=message))

    def _on_scan_closed(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self._update_create_buttons_state()

    def _reload_profiles(self) -> None:
        profiles = self._repo.list_profiles()
        self._profiles = {profile.id: profile for profile in profiles if profile.id is not None}

        self._server_profile_combo.blockSignals(True)
        self._server_profile_combo.clear()
        for profile in profiles:
            if profile.id is None:
                continue
            self._server_profile_combo.addItem(profile.name, profile.id)

        if self._server_profile_combo.count() > 0:
            self._server_profile_combo.setCurrentIndex(0)

        self._server_profile_combo.blockSignals(False)

    def _populate_slot_list(self) -> None:
        self._slots_list.blockSignals(True)
        self._slots_list.clear()

        all_item = QListWidgetItem(tr("backups.singleplayer.all_slots"))
        all_item.setData(Qt.ItemDataRole.UserRole, "ALL")
        all_item.setFlags(all_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        all_item.setCheckState(Qt.CheckState.Unchecked)
        self._slots_list.addItem(all_item)

        for slot_number in sorted(self._slots_by_number.keys()):
            slot = self._slots_by_number[slot_number]
            item = QListWidgetItem(tr("backups.slot_item", slot=slot_number, name=slot.display_name))
            item.setData(Qt.ItemDataRole.UserRole, slot_number)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._slots_list.addItem(item)
        self._slots_list.blockSignals(False)

        self._update_slots_list_height()

        self._update_create_buttons_state()

    def _update_slots_list_height(self) -> None:
        row_count = self._slots_list.count()
        if row_count <= 0:
            self._slots_list.setMinimumHeight(56)
            self._slots_list.setMaximumHeight(56)
            return

        row_height = self._slots_list.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 24

        frame = self._slots_list.frameWidth() * 2
        total_height = (row_height * row_count) + frame + 4
        self._slots_list.setMinimumHeight(total_height)
        self._slots_list.setMaximumHeight(total_height)

    def _start_singleplayer_backup(self) -> None:
        if self._backup_thread is not None or self._scan_result is None:
            return

        selected_slots = self._resolve_selected_slots()
        if len(selected_slots) == 0:
            QMessageBox.warning(self, tr("backups.title"), tr("backups.error.no_slots"))
            return

        backup_root = Path(self._config.get_backup_root_dir())
        self._set_job_ui_state(True)
        self._progress_bar.setValue(0)
        self._status_label.setText(tr("backups.progress.preparing"))

        thread = QThread(self)
        worker = SingleplayerBackupWorker(
            effective_root=self._scan_result.root,
            slots=selected_slots,
            backup_root=backup_root,
            backup_zip_enabled=self._config.get_backup_zip_enabled(),
            backup_keep_uncompressed=self._config.get_backup_keep_uncompressed(),
            logger=self._logger,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_backup_progress)
        worker.success.connect(self._on_backup_success)
        worker.error.connect(self._on_backup_error)
        worker.success.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_backup_thread_closed)

        self._backup_thread = thread
        self._backup_worker = worker
        self._running_server_profile = None
        self._retry_server_requested = False
        self._retry_server_password = None

        thread.start()

    def _start_server_backup_from_selection(self) -> None:
        if self._backup_thread is not None:
            return

        profile = self._selected_profile()
        if profile is None:
            QMessageBox.warning(self, tr("backups.title"), tr("backups.error.no_active_profile"))
            return

        self._start_server_backup(profile=profile, password_override=None)

    def _start_server_backup(self, profile: Profile, password_override: str | None) -> None:
        if self._backup_thread is not None:
            return

        backup_root = Path(self._config.get_backup_root_dir())
        self._set_job_ui_state(True)
        self._progress_bar.setValue(0)
        self._status_label.setText(tr("backups.progress.preparing"))

        thread = QThread(self)
        worker = ServerBackupWorker(
            profile=profile,
            backup_root=backup_root,
            backup_zip_enabled=self._config.get_backup_zip_enabled(),
            backup_keep_uncompressed=self._config.get_backup_keep_uncompressed(),
            logger=self._logger,
            password=password_override,
        )
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_backup_progress)
        worker.need_password.connect(self._on_server_need_password)
        worker.success.connect(self._on_backup_success)
        worker.error.connect(self._on_backup_error)
        worker.success.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_backup_thread_closed)

        self._backup_thread = thread
        self._backup_worker = worker
        self._running_server_profile = profile
        self._retry_server_requested = False
        self._retry_server_password = None

        thread.start()

    def _on_server_need_password(self, profile_name: str) -> None:
        profile = self._running_server_profile
        if profile is None or profile.id is None:
            return

        dialog = PasswordDialog(profile_name=profile_name, parent=self)
        if dialog.exec() != PasswordDialog.DialogCode.Accepted:
            self._retry_server_requested = False
            self._retry_server_password = None
            return

        password = dialog.password()
        if password == "":
            self._retry_server_requested = False
            self._retry_server_password = None
            return

        if dialog.remember_password():
            self._credential_service.set_password(profile.id, profile.username, password)

        self._retry_server_requested = True
        self._retry_server_password = password

    def _on_backup_progress(self, percent: int, message: str) -> None:
        self._progress_bar.setValue(max(0, min(100, percent)))
        self._status_label.setText(message)

    def _on_backup_success(self, result: object) -> None:
        if not isinstance(result, BackupResult):
            return

        if not result.success:
            self._status_label.setText(tr("backups.status.failed", error=result.message))
            QMessageBox.critical(self, tr("common.error"), result.message)
            self._refresh_backup_list()
            return

        self._status_label.setText(tr("backups.status.finished"))
        backup_path = str(result.backup_dir) if result.backup_dir is not None else tr("common.not_available")
        QMessageBox.information(
            self,
            tr("backups.success.title"),
            tr("backups.success.text", path=backup_path),
        )
        self._refresh_backup_list()

    def _on_backup_error(self, message: str) -> None:
        if message == tr("backups.error.password_required") and self._retry_server_requested:
            return

        self._status_label.setText(tr("backups.status.failed", error=message))
        if message == tr("backups.error.game_running.text"):
            QMessageBox.critical(self, tr("backups.error.game_running.title"), message)
            return
        QMessageBox.critical(self, tr("common.error"), tr("backups.status.failed", error=message))

    def _on_backup_thread_closed(self) -> None:
        self._backup_thread = None
        self._backup_worker = None

        if self._retry_server_requested and self._running_server_profile is not None and self._retry_server_password:
            profile = self._running_server_profile
            password = self._retry_server_password
            self._retry_server_requested = False
            self._retry_server_password = None
            self._start_server_backup(profile=profile, password_override=password)
            return

        self._running_server_profile = None
        self._set_job_ui_state(False)
        self._update_create_buttons_state()

    def _resolve_selected_slots(self) -> list[SaveSlot]:
        all_item = self._slots_list.item(0)
        if all_item is not None and all_item.data(Qt.ItemDataRole.UserRole) == "ALL":
            if all_item.checkState() == Qt.CheckState.Checked:
                return [self._slots_by_number[number] for number in sorted(self._slots_by_number.keys())]

        start_index = 1 if all_item is not None and all_item.data(Qt.ItemDataRole.UserRole) == "ALL" else 0

        result: list[SaveSlot] = []
        for idx in range(start_index, self._slots_list.count()):
            item = self._slots_list.item(idx)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            slot_number = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(slot_number, int) and slot_number in self._slots_by_number:
                result.append(self._slots_by_number[slot_number])
        return result

    def _selected_profile(self) -> Profile | None:
        profile_id = self._server_profile_combo.currentData()
        if not isinstance(profile_id, int):
            return None
        return self._profiles.get(profile_id)

    def _on_all_slots_toggled(self, checked: bool) -> None:
        self._slots_list.blockSignals(True)
        for idx in range(1, self._slots_list.count()):
            item = self._slots_list.item(idx)
            if item is None:
                continue
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self._slots_list.blockSignals(False)

        self._update_create_buttons_state()

    def _on_slot_item_changed(self, item: QListWidgetItem) -> None:
        marker = item.data(Qt.ItemDataRole.UserRole)
        if marker == "ALL":
            self._on_all_slots_toggled(item.checkState() == Qt.CheckState.Checked)
            return

        all_item = self._slots_list.item(0)
        if all_item is not None and all_item.data(Qt.ItemDataRole.UserRole) == "ALL":
            if all_item.checkState() == Qt.CheckState.Checked:
                all_item.setCheckState(Qt.CheckState.Unchecked)

        self._update_create_buttons_state()

    def _refresh_backup_list(self) -> None:
        backup_root = Path(self._config.get_backup_root_dir())
        self._backup_entries = list_backups(backup_root)
        self._render_backups_table()

    def _browse_backup_root(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            tr("settings.backup_root.browse_title"),
            self._backup_root_edit.text().strip(),
        )
        if selected_dir:
            self._backup_root_edit.setText(selected_dir)

    def _reset_backup_root(self) -> None:
        self._backup_root_edit.setText(str(Path(self._config.get_backup_root_dir())))

    def _save_backup_settings(self) -> None:
        selected_root = self._backup_root_edit.text().strip()
        if selected_root != "":
            normalized_root = str(Path(selected_root).expanduser().resolve())
            self._config.set_backup_root_dir(normalized_root)
            self._backup_root_edit.setText(normalized_root)

        self._config.set_backup_zip_enabled(self._backup_zip_enabled_checkbox.isChecked())
        self._config.set_backup_keep_uncompressed(self._backup_keep_uncompressed_checkbox.isChecked())
        self._status_label.setText(tr("settings.saved"))
        self._refresh_backup_list()

    def _render_backups_table(self) -> None:
        entries = self._backup_entries
        self._backups_table.setRowCount(len(entries))

        if len(entries) == 0:
            self._backups_table.hide()
            self._no_backups_label.show()
            return

        self._backups_table.show()
        self._no_backups_label.hide()

        header = self._backups_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        for row, entry in enumerate(entries):
            type_text = tr("backups.type.sp") if entry.type == BackupType.SINGLEPLAYER else tr("backups.type.srv")
            date_text = self._format_datetime(entry.created_at)
            size_text = self._format_size(entry.size_bytes)
            format_text = tr("backups.format.zip") if entry.is_zipped else tr("backups.format.folder")

            display_title = entry.display_title
            if len(display_title) > 72:
                display_title = f"{display_title[:69]}..."

            values = [type_text, format_text, date_text, display_title, size_text]
            for column, value in enumerate(values):
                item = self._backups_table.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    self._backups_table.setItem(row, column, item)
                item.setText(value)
                item.setToolTip(str(entry.path))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)

            open_button = QPushButton(tr("backups.action.open"))
            open_button.setObjectName("backupOpenButton")
            open_button.setMinimumWidth(90)
            open_button.clicked.connect(
                lambda _checked=False, path=entry.path: self._open_entry(path)
            )
            actions_layout.addWidget(open_button)

            reveal_button = QPushButton(tr("backups.action.reveal"))
            reveal_button.setObjectName("backupShowButton")
            reveal_button.setMinimumWidth(90)
            reveal_button.clicked.connect(
                lambda _checked=False, path=entry.path: self._reveal_entry(path)
            )
            actions_layout.addWidget(reveal_button)

            delete_button = QPushButton(tr("backups.action.delete"))
            delete_button.setObjectName("backupDeleteButton")
            delete_button.setMinimumWidth(90)
            delete_button.clicked.connect(
                lambda _checked=False, path=entry.path: self._delete_entry(path)
            )
            actions_layout.addWidget(delete_button)

            actions_layout.addStretch(1)
            self._backups_table.setCellWidget(row, 5, actions_widget)

        self._backups_table.resizeRowsToContents()
        self._backups_table.resizeColumnsToContents()

    def _open_entry(self, path: Path) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _reveal_entry(self, path: Path) -> None:
        parent = path.parent if path.is_file() else path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(parent)))

    def _delete_entry(self, path: Path) -> None:
        confirm = QMessageBox.question(
            self,
            tr("backups.delete.title"),
            tr("backups.delete.text", name=path.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except Exception as error:
            QMessageBox.critical(self, tr("common.error"), tr("backups.status.failed", error=str(error)))
            return

        self._refresh_backup_list()

    def _set_job_ui_state(self, running: bool) -> None:
        self._set_status_card_visible(running)
        controls_enabled = not running
        self._singleplayer_create_button.setEnabled(controls_enabled)
        self._server_create_button.setEnabled(controls_enabled)
        self._server_profile_combo.setEnabled(controls_enabled)
        self._backup_root_edit.setEnabled(controls_enabled)
        self._backup_browse_button.setEnabled(controls_enabled)
        self._backup_reset_button.setEnabled(controls_enabled)
        self._backup_zip_enabled_checkbox.setEnabled(controls_enabled)
        self._backup_keep_uncompressed_checkbox.setEnabled(controls_enabled)
        self._settings_save_button.setEnabled(controls_enabled)
        self._create_tabs.setEnabled(controls_enabled)
        self._list_refresh_button.setEnabled(controls_enabled)
        self._slots_list.setEnabled(controls_enabled)

    def _set_status_card_visible(self, visible: bool) -> None:
        self._status_card.setVisible(visible)

    def _update_create_buttons_state(self) -> None:
        if self._backup_thread is not None:
            self._singleplayer_create_button.setEnabled(False)
            self._server_create_button.setEnabled(False)
            return

        slots_available = len(self._slots_by_number) > 0
        slots_selected = any(
            self._slots_list.item(index) is not None
            and self._slots_list.item(index).data(Qt.ItemDataRole.UserRole) != "ALL"
            and self._slots_list.item(index).checkState() == Qt.CheckState.Checked
            for index in range(self._slots_list.count())
        )

        self._singleplayer_create_button.setEnabled(slots_selected)
        self._server_create_button.setEnabled(self._selected_profile() is not None)

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._headline.setText(tr("backups.title"))
        self._create_title.setText(tr("backups.create_title"))
        self._settings_title.setText(tr("settings.paths_title"))
        self._backup_root_label.setText(tr("settings.backup_root.label"))
        self._backup_browse_button.setText(tr("settings.browse"))
        self._backup_reset_button.setText(tr("settings.reset_default"))
        self._backup_zip_enabled_checkbox.setText(tr("backups.settings.zip_enabled"))
        self._backup_keep_uncompressed_checkbox.setText(tr("backups.settings.keep_uncompressed"))
        self._settings_save_button.setText(tr("singleplayer.settings.save"))
        self._status_title.setText(tr("backups.status.title"))
        self._cancel_button.setText(tr("common.cancel"))
        self._create_tabs.setTabText(0, tr("backups.singleplayer.title"))
        self._create_tabs.setTabText(1, tr("backups.server.title"))
        self._singleplayer_create_button.setText(tr("backups.singleplayer.create"))
        self._server_profile_label.setText(tr("backups.server.profile"))
        self._server_create_button.setText(tr("backups.server.create"))
        self._list_title.setText(tr("backups.list.title"))
        self._list_refresh_button.setText(tr("backups.list.refresh"))
        self._no_backups_label.setText(tr("backups.message.empty"))

        self._backups_table.setHorizontalHeaderLabels(
            [
                tr("backups.table.type"),
                tr("backups.table.format"),
                tr("backups.table.date"),
                tr("backups.table.title"),
                tr("backups.table.size"),
                tr("backups.table.actions"),
            ]
        )

        if self._status_label.text().strip() == "":
            self._status_label.setText(tr("backups.status.idle"))

        self._populate_slot_list()
        self._render_backups_table()
        self._update_create_buttons_state()

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

