from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class EVBadge(QLabel):
    def __init__(
        self,
        text: str = "",
        tone: str = "neutral",
        size: str = "md",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("EVBadge")
        self.set_tone(tone)
        self.set_size(size)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_size(self, size: str) -> None:
        self.setProperty("size", size)
        self.style().unpolish(self)
        self.style().polish(self)
