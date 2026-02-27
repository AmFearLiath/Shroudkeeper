from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from i18n.i18n import get_i18n, tr


class SidebarNavigation(QWidget):
    view_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(128)
        self._order = [
            "dashboard",
            "singleplayer",
            "server",
            "transfers",
            "backups",
            "automations",
            "settings",
        ]
        self._label_keys = {
            "dashboard": "nav.dashboard",
            "singleplayer": "nav.singleplayer",
            "server": "nav.multiplayer",
            "transfers": "nav.transfers",
            "backups": "nav.backups",
            "automations": "nav.automations",
            "settings": "nav.settings",
        }
        self._buttons: dict[str, QPushButton] = {}
        self._current_view = "dashboard"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(10)

        for view_id in self._order:
            button = QPushButton()
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setProperty("nav", True)
            button.setProperty("active", "false")
            button.clicked.connect(lambda _checked=False, value=view_id: self.select_view(value, emit_signal=True))
            layout.addWidget(button)
            self._buttons[view_id] = button

        layout.addStretch(1)
        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()
        self.select_view("dashboard", emit_signal=False)

    def select_view(self, view_id: str, emit_signal: bool) -> None:
        if view_id not in self._buttons:
            return

        self._current_view = view_id
        for button_id, button in self._buttons.items():
            is_active = button_id == view_id
            button.setChecked(is_active)
            button.setProperty("active", "true" if is_active else "false")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

        if emit_signal:
            self.view_selected.emit(view_id)

    def retranslate_ui(self, _language: str | None = None) -> None:
        for view_id, button in self._buttons.items():
            button.setText(tr(self._label_keys[view_id]))
