from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import PurePosixPath

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.profiles.credentials import CredentialService
from core.profiles.models import Profile
from core.remote.client_factory import create_client
from core.remote.test_worker import RemoteTestWorker
from core.server.server_models import ServerScanResult
from core.server.server_world_service import ServerWorldService
from i18n.i18n import get_i18n, tr
from storage.repositories import ProfileRepository
from ui.components.ev_page_header import EVPageHeader
from ui.widgets.multiplayer_config_dialog import MultiplayerConfigDialog
from ui.widgets.multiplayer_saves_dialog import MultiplayerSavesDialog
from ui.widgets.password_dialog import PasswordDialog
from ui.widgets.profile_dialog import ProfileDialog


class ProfilesView(QWidget):
    profiles_changed = Signal()

    def __init__(self, connection: sqlite3.Connection, config: AppConfig, logger: logging.Logger) -> None:
        super().__init__()
        self._logger = logger
        self._config = config
        self._repo = ProfileRepository(connection)
        self._credential_service = CredentialService()

        self._profiles_by_id: dict[int, Profile] = {}
        self._test_thread: QThread | None = None
        self._test_worker: RemoteTestWorker | None = None
        self._startup_test_queue: list[tuple[int, Profile, str]] = []
        self._startup_test_active_profile_id: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._header = EVPageHeader()

        self._add_button = QPushButton()
        self._add_button.setProperty("variant", "secondary")
        self._add_button.clicked.connect(self._on_add_profile)
        self._header.add_action(self._add_button)

        self._edit_button = QPushButton()
        self._edit_button.setProperty("variant", "secondary")
        self._edit_button.clicked.connect(self._on_edit_profile)
        self._header.add_action(self._edit_button)

        self._delete_button = QPushButton()
        self._delete_button.setProperty("variant", "danger")
        self._delete_button.clicked.connect(self._on_delete_profile)
        self._header.add_action(self._delete_button)

        self._test_button = QPushButton()
        self._test_button.setProperty("variant", "primary")
        self._test_button.clicked.connect(self._on_test_connection)
        self._header.add_action(self._test_button)

        layout.addWidget(self._header)

        card = QFrame()
        card.setObjectName("EVCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(10)

        self._profiles_table = QTableWidget(0, 7)
        self._profiles_table.setObjectName("EVTable")
        self._profiles_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._profiles_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._profiles_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._profiles_table.setAlternatingRowColors(True)
        self._profiles_table.verticalHeader().setVisible(False)
        self._profiles_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._profiles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._profiles_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._profiles_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._profiles_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._profiles_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._profiles_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._profiles_table.itemSelectionChanged.connect(self._update_button_states)
        card_layout.addWidget(self._profiles_table, 1)

        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")
        card_layout.addWidget(self._status_label)

        layout.addWidget(card, 1)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self._reload_profiles()
        self.retranslate_ui()
        self._update_button_states()
        QTimer.singleShot(0, self._start_startup_connection_checks)

    def _start_startup_connection_checks(self) -> None:
        profiles = [profile for profile in self._repo.list_profiles() if profile.id is not None]
        self._startup_test_queue = []

        for profile in profiles:
            if profile.id is None:
                continue
            stored_password = self._credential_service.get_password(profile.id, profile.username)
            if not stored_password:
                self._config.set_profile_connection_ok(profile.id, False)
                continue
            self._startup_test_queue.append((profile.id, profile, stored_password))

        self._run_next_startup_connection_check()

    def _run_next_startup_connection_check(self) -> None:
        if self._test_thread is not None:
            return
        if len(self._startup_test_queue) == 0:
            self._startup_test_active_profile_id = None
            return

        profile_id, profile, password = self._startup_test_queue.pop(0)
        self._startup_test_active_profile_id = profile_id

        thread = QThread(self)
        worker = RemoteTestWorker(profile=profile, password=password, logger=self._logger)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_startup_test_finished)
        worker.failed.connect(self._on_startup_test_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_startup_test_thread_closed)

        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _reload_profiles(self) -> None:
        profiles = self._repo.list_profiles()
        profile_status = self._config.get_profile_connection_status()
        self._profiles_by_id = {profile.id: profile for profile in profiles if profile.id is not None}

        self._profiles_table.setRowCount(len(profiles))

        for row_index, profile in enumerate(profiles):
            status_ok = bool(profile.id is not None and profile_status.get(profile.id, False))
            name_text = f"●  {profile.name}"
            self._set_item(row_index, 0, name_text)
            self._set_item(row_index, 1, profile.protocol.upper())
            self._set_item(row_index, 2, profile.host)
            self._set_item(row_index, 3, str(profile.port))
            self._set_item(row_index, 4, profile.username)
            self._set_item(row_index, 5, profile.remote_path)

            name_item = self._profiles_table.item(row_index, 0)
            if name_item is not None:
                name_item.setForeground(QColor("#2fa35c") if status_ok else QColor("#c43e3e"))

            row_anchor = self._profiles_table.item(row_index, 0)
            if row_anchor is not None and profile.id is not None:
                row_anchor.setData(Qt.ItemDataRole.UserRole, profile.id)

            if profile.id is not None:
                self._profiles_table.setCellWidget(row_index, 6, self._build_actions_widget(profile.id))

        self._profiles_table.resizeRowsToContents()
        self.profiles_changed.emit()

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        self._profiles_table.setItem(row, column, item)

    def _build_actions_widget(self, profile_id: int) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        details_button = QPushButton(tr("profiles.action.details"))
        details_button.setProperty("variant", "secondary")
        details_button.clicked.connect(lambda _checked=False, pid=profile_id: self._open_profile_details(pid))
        row.addWidget(details_button)

        config_button = QPushButton(tr("profiles.action.config"))
        config_button.setProperty("variant", "secondary")
        config_button.clicked.connect(lambda _checked=False, pid=profile_id: self._open_profile_config(pid))
        row.addWidget(config_button)
        return container

    def _resolve_password(self, profile: Profile) -> str | None:
        if profile.id is None:
            return None
        password = self._credential_service.get_password(profile.id, profile.username)
        if password:
            return password

        password_dialog = PasswordDialog(profile_name=profile.name, parent=self)
        if password_dialog.exec() != PasswordDialog.DialogCode.Accepted:
            return None

        password = password_dialog.password()
        if password == "":
            return None
        if password_dialog.remember_password():
            self._credential_service.set_password(profile.id, profile.username, password)
        return password

    def _open_profile_details(self, profile_id: int) -> None:
        profile = self._repo.get_profile(profile_id)
        if profile is None:
            return

        password = self._resolve_password(profile)
        if not password:
            return

        try:
            result = asyncio.run(self._scan_profile_world(profile, password))
        except Exception as error:
            QMessageBox.warning(self, tr("common.error"), str(error))
            return

        dialog = MultiplayerSavesDialog(
            profile_name=profile.name,
            result=result,
            rollback_handler=lambda roll: self._rollback_profile_world_sync(profile, password, roll),
            parent=self,
        )
        dialog.exec()

    async def _scan_profile_world(self, profile: Profile, password: str):
        client = create_client(profile=profile, password=password, logger=self._logger)
        success, message = await client.test_connection()
        if not success:
            raise RuntimeError(message)
        service = ServerWorldService(logger=self._logger)
        return await service.scan_server_world(client=client, remote_root=profile.remote_path)

    def _rollback_profile_world_sync(
        self,
        profile: Profile,
        password: str,
        roll_index: int,
    ) -> tuple[bool, str, ServerScanResult | None]:
        try:
            updated_result = asyncio.run(self._rollback_profile_world(profile, password, roll_index))
            return True, "ok", updated_result
        except Exception as error:
            return False, str(error), None

    async def _rollback_profile_world(self, profile: Profile, password: str, roll_index: int):
        client = create_client(profile=profile, password=password, logger=self._logger)
        success, message = await client.test_connection()
        if not success:
            raise RuntimeError(message)

        service = ServerWorldService(logger=self._logger)
        write_ok, write_message = await service.write_latest(
            client=client,
            remote_root=profile.remote_path,
            latest=roll_index,
        )
        if not write_ok:
            raise RuntimeError(write_message)

        return await service.scan_server_world(client=client, remote_root=profile.remote_path)

    def _open_profile_config(self, profile_id: int) -> None:
        profile = self._repo.get_profile(profile_id)
        if profile is None:
            return

        password = self._resolve_password(profile)
        if not password:
            return

        try:
            remote_path, payload = asyncio.run(self._download_server_config(profile, password))
        except Exception as error:
            QMessageBox.warning(self, tr("common.error"), str(error))
            return

        dialog = MultiplayerConfigDialog(profile_name=profile.name, remote_path=remote_path, payload=payload, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated_payload = dialog.payload()
        try:
            asyncio.run(self._upload_server_config(profile, password, remote_path, updated_payload))
        except Exception as error:
            QMessageBox.warning(self, tr("common.error"), str(error))
            return

        QMessageBox.information(self, tr("common.ok"), tr("profiles.config.saved"))

    async def _download_server_config(self, profile: Profile, password: str) -> tuple[str, dict[str, object]]:
        client = create_client(profile=profile, password=password, logger=self._logger)
        success, message = await client.test_connection()
        if not success:
            raise RuntimeError(message)

        normalized_remote_root = "/" + "/".join(part for part in profile.remote_path.strip().split("/") if part)
        normalized_remote_root = normalized_remote_root if normalized_remote_root != "" else "/"
        config_dir = str(PurePosixPath(normalized_remote_root).parent)
        config_path = str(PurePosixPath(config_dir) / "enshrouded_server.json")

        read_ok, read_message, payload_bytes = await client.read_file_bytes(config_path, max_bytes=2 * 1024 * 1024)
        if not read_ok or payload_bytes is None:
            raise RuntimeError(read_message)

        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as error:
            raise RuntimeError(str(error))

        if not isinstance(payload, dict):
            raise RuntimeError(tr("multiplayer.config.invalid_json_root"))

        return config_path, payload

    async def _upload_server_config(
        self,
        profile: Profile,
        password: str,
        config_path: str,
        payload: dict[str, object],
    ) -> None:
        client = create_client(profile=profile, password=password, logger=self._logger)
        success, message = await client.test_connection()
        if not success:
            raise RuntimeError(message)

        data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        upload_ok, upload_message, _bytes_written = await client.upload_bytes(config_path, data)
        if not upload_ok:
            raise RuntimeError(upload_message)

    def _selected_profile(self) -> Profile | None:
        selected_ranges = self._profiles_table.selectedRanges()
        if not selected_ranges:
            return None

        row = selected_ranges[0].topRow()
        anchor = self._profiles_table.item(row, 0)
        if anchor is None:
            return None

        profile_id = anchor.data(Qt.ItemDataRole.UserRole)
        if profile_id is None:
            return None

        return self._profiles_by_id.get(int(profile_id))

    def _on_add_profile(self) -> None:
        dialog = ProfileDialog(parent=self)
        if dialog.exec() != ProfileDialog.DialogCode.Accepted:
            return

        profile = dialog.get_profile()
        profile_id = self._repo.create_profile(profile)
        self._config.set_profile_connection_ok(profile_id, False)
        self._reload_profiles()
        self._status_label.setText(tr("profiles.message.saved"))

    def _on_edit_profile(self) -> None:
        profile = self._selected_profile()
        if profile is None:
            QMessageBox.information(self, tr("profiles.title"), tr("profiles.message.no_selection"))
            return

        dialog = ProfileDialog(profile=profile, parent=self)
        if dialog.exec() != ProfileDialog.DialogCode.Accepted:
            return

        confirmed = QMessageBox.question(
            self,
            tr("profiles.confirm.overwrite.title"),
            tr("profiles.confirm.overwrite.text", name=profile.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        updated_profile = dialog.get_profile()
        self._repo.update_profile(updated_profile)
        if updated_profile.id is not None:
            self._config.set_profile_connection_ok(updated_profile.id, False)
        self._reload_profiles()
        self._status_label.setText(tr("profiles.message.saved"))

    def _on_delete_profile(self) -> None:
        profile = self._selected_profile()
        if profile is None:
            QMessageBox.information(self, tr("profiles.title"), tr("profiles.message.no_selection"))
            return

        confirmed = QMessageBox.question(
            self,
            tr("profiles.confirm.delete.title"),
            tr("profiles.confirm.delete.text", name=profile.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        if profile.id is not None:
            self._repo.delete_profile(profile.id)
            self._config.remove_profile_connection_status(profile.id)
            try:
                self._credential_service.delete_password(profile.id, profile.username)
            except Exception:
                pass

        self._reload_profiles()
        self._status_label.setText(tr("profiles.message.deleted"))

    def _on_test_connection(self) -> None:
        if self._test_thread is not None:
            return

        profile = self._selected_profile()
        if profile is None:
            QMessageBox.information(self, tr("profiles.title"), tr("profiles.message.no_selection"))
            return
        if profile.id is None:
            QMessageBox.warning(self, tr("profiles.title"), tr("profiles.message.no_selection"))
            return

        password = self._credential_service.get_password(profile.id, profile.username)
        if not password:
            password_dialog = PasswordDialog(profile_name=profile.name, parent=self)
            if password_dialog.exec() != PasswordDialog.DialogCode.Accepted:
                return

            password = password_dialog.password()
            if password_dialog.remember_password() and password:
                self._credential_service.set_password(profile.id, profile.username, password)

        self._status_label.setText(tr("profiles.test.running"))
        self._set_testing_ui_state(True)

        thread = QThread(self)
        worker = RemoteTestWorker(profile=profile, password=password, logger=self._logger)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_test_finished)
        worker.failed.connect(self._on_test_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_test_thread_closed)

        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _on_test_finished(self, success: bool, message: str) -> None:
        self._set_testing_ui_state(False)
        if success:
            selected = self._selected_profile()
            if selected is not None and selected.id is not None:
                self._config.set_profile_connection_ok(selected.id, True)
            self._reload_profiles()
            self._status_label.setText(tr("profiles.test.success.text", message=message))
            QMessageBox.information(
                self,
                tr("profiles.test.success.title"),
                tr("profiles.test.success.text", message=message),
            )
            self._logger.info("Remote profile connection test successful")
        else:
            selected = self._selected_profile()
            if selected is not None and selected.id is not None:
                self._config.set_profile_connection_ok(selected.id, False)
            self._reload_profiles()
            self._status_label.setText(tr("profiles.test.failed.text", message=message))
            QMessageBox.warning(
                self,
                tr("profiles.test.failed.title"),
                tr("profiles.test.failed.text", message=message),
            )
            self._logger.warning("Remote profile connection test failed")

    def _on_test_failed(self, message: str) -> None:
        selected = self._selected_profile()
        if selected is not None and selected.id is not None:
            self._config.set_profile_connection_ok(selected.id, False)
        self._set_testing_ui_state(False)
        self._status_label.setText(tr("profiles.test.failed.text", message=message))
        QMessageBox.warning(self, tr("profiles.test.failed.title"), tr("profiles.test.failed.text", message=message))
        self._logger.warning("Remote profile connection test failed")
        self._reload_profiles()

    def _on_test_thread_closed(self) -> None:
        self._test_thread = None
        self._test_worker = None
        self._set_testing_ui_state(False)

    def _on_startup_test_finished(self, success: bool, _message: str) -> None:
        profile_id = self._startup_test_active_profile_id
        if profile_id is None:
            return
        self._config.set_profile_connection_ok(profile_id, bool(success))
        self._reload_profiles()

    def _on_startup_test_failed(self, _message: str) -> None:
        profile_id = self._startup_test_active_profile_id
        if profile_id is None:
            return
        self._config.set_profile_connection_ok(profile_id, False)
        self._reload_profiles()

    def _on_startup_test_thread_closed(self) -> None:
        self._test_thread = None
        self._test_worker = None
        self._run_next_startup_connection_check()

    def _set_testing_ui_state(self, is_testing: bool) -> None:
        self._add_button.setEnabled(not is_testing)
        self._edit_button.setEnabled(not is_testing)
        self._delete_button.setEnabled(not is_testing)
        self._test_button.setEnabled(not is_testing)
        self._profiles_table.setEnabled(not is_testing)

    def _update_button_states(self) -> None:
        selected = self._selected_profile() is not None
        self._edit_button.setEnabled(selected and self._test_thread is None)
        self._delete_button.setEnabled(selected and self._test_thread is None)
        self._test_button.setEnabled(selected and self._test_thread is None)

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("profiles.title"))
        self._add_button.setText(tr("profiles.action.add"))
        self._edit_button.setText(tr("profiles.action.edit"))
        self._delete_button.setText(tr("profiles.action.delete"))
        self._test_button.setText(tr("profiles.action.test"))

        self._profiles_table.setHorizontalHeaderLabels(
            [
                tr("profiles.table.name"),
                tr("profiles.table.protocol"),
                tr("profiles.table.host"),
                tr("profiles.table.port"),
                tr("profiles.table.username"),
                tr("profiles.table.remote_path"),
                tr("profiles.table.actions"),
            ]
        )

        self._reload_profiles()
        if self._status_label.text().strip() == "":
            self._status_label.setText(tr("profiles.description"))
