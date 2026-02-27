from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.profiles.models import Profile
from i18n.i18n import get_i18n, tr


class ProfileDialog(QDialog):
    _DEFAULT_PORTS: dict[str, int] = {"ftp": 21, "ftps": 21, "sftp": 22}

    def __init__(self, profile: Profile | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source_profile = profile
        self._last_protocol = profile.protocol if profile is not None else "sftp"
        self._last_default_port = self._DEFAULT_PORTS[self._last_protocol]

        self.setObjectName("profileDialog")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setObjectName("panelTitle")
        layout.addWidget(self._title_label)

        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self._form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self._form.setHorizontalSpacing(12)
        self._form.setVerticalSpacing(10)

        self._field_labels: dict[str, QLabel] = {}

        self._name_input = QLineEdit()
        self._form.addRow(self._build_label("name"), self._name_input)

        self._protocol_input = QComboBox()
        self._protocol_input.currentIndexChanged.connect(self._on_protocol_changed)
        self._form.addRow(self._build_label("protocol"), self._protocol_input)

        self._host_input = QLineEdit()
        self._form.addRow(self._build_label("host"), self._host_input)

        self._port_input = QSpinBox()
        self._port_input.setRange(1, 65535)
        self._form.addRow(self._build_label("port"), self._port_input)

        self._username_input = QLineEdit()
        self._form.addRow(self._build_label("username"), self._username_input)

        self._remote_path_input = QLineEdit()
        self._form.addRow(self._build_label("remote_path"), self._remote_path_input)

        self._passive_mode_input = QCheckBox()
        self._form.addRow(self._build_label("passive_mode"), self._passive_mode_input)

        self._verify_host_key_input = QCheckBox()
        self._form.addRow(self._build_label("verify_host_key"), self._verify_host_key_input)

        layout.addLayout(self._form)

        button_row = QHBoxLayout()
        button_row.addStretch(1)

        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self._cancel_button)

        self._save_button = QPushButton()
        self._save_button.setObjectName("primaryButton")
        self._save_button.clicked.connect(self._on_save_clicked)
        button_row.addWidget(self._save_button)

        layout.addLayout(button_row)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self._fill_from_source()
        self.retranslate_ui()

    def _build_label(self, key: str) -> QLabel:
        label = QLabel()
        self._field_labels[key] = label
        return label

    def _fill_from_source(self) -> None:
        if self._source_profile is None:
            self._name_input.setText("")
            self._host_input.setText("")
            self._username_input.setText("")
            self._remote_path_input.setText("/savegame")
            self._passive_mode_input.setChecked(True)
            self._verify_host_key_input.setChecked(True)
        else:
            self._name_input.setText(self._source_profile.name)
            self._host_input.setText(self._source_profile.host)
            self._username_input.setText(self._source_profile.username)
            self._remote_path_input.setText(self._source_profile.remote_path)
            self._passive_mode_input.setChecked(self._source_profile.passive_mode)
            self._verify_host_key_input.setChecked(self._source_profile.verify_host_key)

        self._protocol_input.clear()
        self._protocol_input.addItem("FTP", "ftp")
        self._protocol_input.addItem("FTPS", "ftps")
        self._protocol_input.addItem("SFTP", "sftp")

        protocol = self._source_profile.protocol if self._source_profile is not None else "sftp"
        index = self._protocol_input.findData(protocol)
        self._protocol_input.setCurrentIndex(index if index >= 0 else 2)

        if self._source_profile is None:
            self._port_input.setValue(self._DEFAULT_PORTS[protocol])
        else:
            self._port_input.setValue(self._source_profile.port)

        self._update_protocol_specific_fields()

    def _on_protocol_changed(self) -> None:
        protocol = str(self._protocol_input.currentData())
        default_port = self._DEFAULT_PORTS.get(protocol, 22)
        if self._port_input.value() == self._last_default_port:
            self._port_input.setValue(default_port)
        self._last_protocol = protocol
        self._last_default_port = default_port
        self._update_protocol_specific_fields()

    def _update_protocol_specific_fields(self) -> None:
        protocol = str(self._protocol_input.currentData())
        is_sftp = protocol == "sftp"

        self._passive_mode_input.setVisible(not is_sftp)
        self._verify_host_key_input.setVisible(is_sftp)

        passive_label = self._form.labelForField(self._passive_mode_input)
        verify_label = self._form.labelForField(self._verify_host_key_input)
        if passive_label is not None:
            passive_label.setVisible(not is_sftp)
        if verify_label is not None:
            verify_label.setVisible(is_sftp)

    def _on_save_clicked(self) -> None:
        if not self._validate_inputs():
            return
        self.accept()

    def _validate_inputs(self) -> bool:
        if self._name_input.text().strip() == "":
            QMessageBox.warning(self, tr("profile_dialog.validation.title"), tr("profile_dialog.validation.name_required"))
            return False
        if self._host_input.text().strip() == "":
            QMessageBox.warning(self, tr("profile_dialog.validation.title"), tr("profile_dialog.validation.host_required"))
            return False
        if self._username_input.text().strip() == "":
            QMessageBox.warning(self, tr("profile_dialog.validation.title"), tr("profile_dialog.validation.username_required"))
            return False
        if self._remote_path_input.text().strip() == "":
            QMessageBox.warning(
                self,
                tr("profile_dialog.validation.title"),
                tr("profile_dialog.validation.remote_path_required"),
            )
            return False
        return True

    def get_profile(self) -> Profile:
        protocol = str(self._protocol_input.currentData())
        normalized_path = self._normalize_remote_path(self._remote_path_input.text())

        profile = Profile(
            id=self._source_profile.id if self._source_profile is not None else None,
            name=self._name_input.text().strip(),
            protocol=protocol,
            host=self._host_input.text().strip(),
            port=int(self._port_input.value()),
            username=self._username_input.text().strip(),
            remote_path=normalized_path,
            passive_mode=self._passive_mode_input.isChecked(),
            verify_host_key=self._verify_host_key_input.isChecked(),
            created_at=self._source_profile.created_at if self._source_profile is not None else None,
            updated_at=self._source_profile.updated_at if self._source_profile is not None else None,
        )
        return profile

    def _normalize_remote_path(self, raw_path: str) -> str:
        normalized = "/" + "/".join(part for part in raw_path.strip().split("/") if part)
        return normalized if normalized != "" else "/"

    def retranslate_ui(self, _language: str | None = None) -> None:
        if self._source_profile is None:
            self.setWindowTitle(tr("profile_dialog.title.add"))
            self._title_label.setText(tr("profile_dialog.title.add"))
        else:
            title = tr("profile_dialog.title.edit", name=self._source_profile.name)
            self.setWindowTitle(title)
            self._title_label.setText(title)

        for key, label in self._field_labels.items():
            label.setText(tr(f"profile_dialog.field.{key}"))

        self._passive_mode_input.setText(tr("profile_dialog.field.passive_mode"))
        self._verify_host_key_input.setText(tr("profile_dialog.field.verify_host_key"))
        self._save_button.setText(tr("profile_dialog.save"))
        self._cancel_button.setText(tr("profile_dialog.cancel"))
