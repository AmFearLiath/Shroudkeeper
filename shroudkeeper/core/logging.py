from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Signal

from core.paths import get_logs_dir


class LogEmitter(QObject):
    log_message = Signal(str)


class QtSignalLogHandler(logging.Handler):
    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__()
        self._emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self._emitter.log_message.emit(message)
        except Exception:
            self.handleError(record)


def setup_logging() -> tuple[logging.Logger, LogEmitter]:
    logs_dir = get_logs_dir()
    log_file = logs_dir / "app.log"

    logger = logging.getLogger("shroudkeeper")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    emitter = LogEmitter()
    signal_handler = QtSignalLogHandler(emitter)
    signal_handler.setFormatter(formatter)
    signal_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(signal_handler)

    return logger, emitter
