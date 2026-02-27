from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class EVCard(QFrame):
    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EVCard")
        self.setProperty("variant", "default")

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(12, 12, 12, 12)
        self._root_layout.setSpacing(10)

        self._header_widget = QWidget(self)
        self._header_layout = QHBoxLayout(self._header_widget)
        self._header_layout.setContentsMargins(0, 0, 0, 0)
        self._header_layout.setSpacing(8)

        self._title_label = QLabel(self._header_widget)
        self._title_label.setObjectName("H2")
        self._header_layout.addWidget(self._title_label, 1)

        self._actions_widget = QWidget(self._header_widget)
        self._actions_layout = QHBoxLayout(self._actions_widget)
        self._actions_layout.setContentsMargins(0, 0, 0, 0)
        self._actions_layout.setSpacing(6)
        self._header_layout.addWidget(self._actions_widget, 0)

        self._header_widget.setVisible(False)
        self._root_layout.addWidget(self._header_widget)

        self._body_layout = QVBoxLayout()
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(10)
        self._root_layout.addLayout(self._body_layout, 1)

        if title is not None:
            self.set_title(title)

    def set_variant(self, variant: str) -> None:
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_padding(self, padding: int) -> None:
        self._root_layout.setContentsMargins(padding, padding, padding, padding)

    def set_title(self, title: str | None) -> None:
        visible = title is not None and title.strip() != ""
        self._title_label.setText(title or "")
        self._header_widget.setVisible(visible or self._actions_layout.count() > 0)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def actions_layout(self) -> QHBoxLayout:
        self._header_widget.setVisible(True)
        return self._actions_layout
