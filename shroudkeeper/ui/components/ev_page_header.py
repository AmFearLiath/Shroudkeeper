from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class EVPageHeader(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")
        self.setProperty("hasActions", "false")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(10)

        self._title_label = QLabel()
        self._title_label.setObjectName("PageTitle")
        self._title_label.setVisible(False)
        self._layout.addWidget(self._title_label, 1)

        self._actions_host = QWidget(self)
        self._actions_layout = QHBoxLayout(self._actions_host)
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(8)
        self._layout.addWidget(self._actions_host)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def add_action(self, action_widget: QWidget) -> None:
        self._actions_layout.addWidget(action_widget)
        self._refresh_actions_property()

    def clear_actions(self) -> None:
        while self._actions_layout.count() > 0:
            item = self._actions_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self._refresh_actions_property()

    def _refresh_actions_property(self) -> None:
        has_actions = self._actions_layout.count() > 0
        self.setProperty("hasActions", "true" if has_actions else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
