from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from i18n.i18n import get_i18n, tr


class BackupRestoreDialog(QDialog):
    TARGET_SINGLEPLAYER = "singleplayer"
    TARGET_MULTIPLAYER = "multiplayer"

    def __init__(
        self,
        slot_options: list[tuple[int, str]],
        profile_options: list[tuple[int, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._slot_options = slot_options
        self._profile_options = profile_options

        self.setObjectName("backupRestoreDialog")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._target_label = QLabel()
        layout.addWidget(self._target_label)

        self._target_combo = QComboBox()
        self._target_combo.currentIndexChanged.connect(self._update_visibility)
        layout.addWidget(self._target_combo)

        self._slot_label = QLabel()
        layout.addWidget(self._slot_label)

        self._slot_combo = QComboBox()
        layout.addWidget(self._slot_combo)

        self._profile_label = QLabel()
        layout.addWidget(self._profile_label)

        self._profile_combo = QComboBox()
        layout.addWidget(self._profile_combo)

        self._server_hint = QLabel()
        self._server_hint.setWordWrap(True)
        self._server_hint.setObjectName("infoBar")
        self._server_hint.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._server_hint)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self._cancel_button)

        self._ok_button = QPushButton()
        self._ok_button.setObjectName("primaryButton")
        self._ok_button.clicked.connect(self.accept)
        button_row.addWidget(self._ok_button)

        layout.addLayout(button_row)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def selected_target(self) -> str:
        value = self._target_combo.currentData()
        if isinstance(value, str):
            return value
        return self.TARGET_SINGLEPLAYER

    def selected_slot(self) -> int | None:
        value = self._slot_combo.currentData()
        if isinstance(value, int):
            return value
        return None

    def selected_profile_id(self) -> int | None:
        value = self._profile_combo.currentData()
        if isinstance(value, int):
            return value
        return None

    def _update_visibility(self) -> None:
        target = self.selected_target()
        singleplayer_selected = target == self.TARGET_SINGLEPLAYER

        self._slot_label.setVisible(singleplayer_selected)
        self._slot_combo.setVisible(singleplayer_selected)

        self._profile_label.setVisible(not singleplayer_selected)
        self._profile_combo.setVisible(not singleplayer_selected)
        self._server_hint.setVisible(not singleplayer_selected)

        slot_available = self._slot_combo.count() > 0
        profile_available = self._profile_combo.count() > 0

        if singleplayer_selected:
            self._ok_button.setEnabled(slot_available)
        else:
            self._ok_button.setEnabled(profile_available)

    def retranslate_ui(self, _language: str | None = None) -> None:
        self.setWindowTitle(tr("backups.restore.dialog.title"))

        self._target_label.setText(tr("backups.restore.target"))
        self._slot_label.setText(tr("backups.restore.slot"))
        self._profile_label.setText(tr("backups.restore.profile"))
        self._server_hint.setText(tr("backups.restore.warning.server_stopped"))

        self._cancel_button.setText(tr("common.cancel"))
        self._ok_button.setText(tr("common.ok"))

        self._target_combo.blockSignals(True)
        current_target = self.selected_target()
        self._target_combo.clear()
        self._target_combo.addItem(tr("backups.restore.target.singleplayer"), self.TARGET_SINGLEPLAYER)
        self._target_combo.addItem(tr("backups.restore.target.multiplayer"), self.TARGET_MULTIPLAYER)

        target_index = self._target_combo.findData(current_target)
        if target_index < 0:
            target_index = 0
        self._target_combo.setCurrentIndex(target_index)
        self._target_combo.blockSignals(False)

        current_slot = self.selected_slot()
        self._slot_combo.clear()
        for slot_number, text in self._slot_options:
            self._slot_combo.addItem(text, slot_number)

        if current_slot is not None:
            slot_index = self._slot_combo.findData(current_slot)
            if slot_index >= 0:
                self._slot_combo.setCurrentIndex(slot_index)

        current_profile = self.selected_profile_id()
        self._profile_combo.clear()
        for profile_id, name in self._profile_options:
            self._profile_combo.addItem(name, profile_id)

        if current_profile is not None:
            profile_index = self._profile_combo.findData(current_profile)
            if profile_index >= 0:
                self._profile_combo.setCurrentIndex(profile_index)

        self._update_visibility()
