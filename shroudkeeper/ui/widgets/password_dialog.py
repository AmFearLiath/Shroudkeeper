from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from i18n.i18n import get_i18n, tr


class PasswordDialog(QDialog):
    def __init__(self, profile_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile_name = profile_name

        self.setObjectName("passwordDialog")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._prompt = QLabel()
        self._prompt.setWordWrap(True)
        layout.addWidget(self._prompt)

        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self._password_input)

        self._remember_checkbox = QCheckBox()
        layout.addWidget(self._remember_checkbox)

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

    def password(self) -> str:
        return self._password_input.text()

    def remember_password(self) -> bool:
        return self._remember_checkbox.isChecked()

    def retranslate_ui(self, _language: str | None = None) -> None:
        self.setWindowTitle(tr("password_dialog.title"))
        self._prompt.setText(tr("password_dialog.prompt", profile_name=self._profile_name))
        self._remember_checkbox.setText(tr("password_dialog.remember"))
        self._ok_button.setText(tr("password_dialog.ok"))
        self._cancel_button.setText(tr("password_dialog.cancel"))
