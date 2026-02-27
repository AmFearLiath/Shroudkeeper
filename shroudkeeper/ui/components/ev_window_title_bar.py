from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStyle, QWidget


class EVWindowTitleBar(QWidget):
    minimize_requested = Signal()
    maximize_requested = Signal()
    restore_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("WindowTitleBar")
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._title_label = QLabel()
        self._title_label.setObjectName("WindowTitle")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._title_label, 1)

        self._minimize_button = QPushButton()
        self._minimize_button.setObjectName("TitleBarButton")
        self._minimize_button.setProperty("variant", "ghost")
        self._minimize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self._minimize_button.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self._minimize_button)

        self._maximize_button = QPushButton()
        self._maximize_button.setObjectName("TitleBarButton")
        self._maximize_button.setProperty("variant", "ghost")
        self._maximize_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        layout.addWidget(self._maximize_button)

        self._close_button = QPushButton()
        self._close_button.setObjectName("TitleBarCloseButton")
        self._close_button.setProperty("variant", "ghost")
        self._close_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self._close_button.clicked.connect(self.close_requested.emit)
        layout.addWidget(self._close_button)

        self._maximize_button.clicked.connect(self._on_toggle_maximize)
        self._is_maximized = False

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_maximized(self, maximized: bool) -> None:
        self._is_maximized = maximized
        icon = (
            QStyle.StandardPixmap.SP_TitleBarNormalButton
            if maximized
            else QStyle.StandardPixmap.SP_TitleBarMaxButton
        )
        self._maximize_button.setIcon(self.style().standardIcon(icon))

    def _on_toggle_maximize(self) -> None:
        if self._is_maximized:
            self.restore_requested.emit()
        else:
            self.maximize_requested.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            if window is not None and not window.isMaximized():
                handle = window.windowHandle()
                if handle is not None and handle.startSystemMove():
                    event.accept()
                    return
        super().mousePressEvent(event)
