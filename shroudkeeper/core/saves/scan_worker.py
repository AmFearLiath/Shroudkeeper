from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from core.saves.models import SaveScanResult
from core.saves.scanner_service import SaveScannerService


class SaveScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, scanner: SaveScannerService, root: Path) -> None:
        super().__init__()
        self._scanner = scanner
        self._root = root

    @Slot()
    def run(self) -> None:
        try:
            result: SaveScanResult = self._scanner.scan_singleplayer(self._root)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
