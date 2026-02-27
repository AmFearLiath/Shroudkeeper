from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.config import AppConfig
from core.logging import setup_logging
from core.paths import ensure_runtime_directories
from core.resources import resource_path
from core.theme.theme_loader import apply_theme
from i18n.i18n import initialize_i18n, tr
from storage.db import DatabaseManager
from ui.main_window import MainWindow


def _normalize_application_font(app: QApplication) -> None:
    app_font = app.font()
    if app_font.pointSize() > 0:
        return

    pixel_size = app_font.pixelSize()
    if pixel_size > 0:
        screen = app.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen is not None else 96.0
        point_size = max(1, int(round(pixel_size * 72.0 / dpi)))
    else:
        point_size = 10

    app_font.setPointSize(point_size)
    app.setFont(app_font)


def main() -> int:
    ensure_runtime_directories()

    app = QApplication(sys.argv)
    _normalize_application_font(app)
    app_icon = QIcon(str(resource_path("assets/icons/icon.png")))
    app.setWindowIcon(app_icon)

    config = AppConfig()
    initialize_i18n(config.get_language())

    logger, log_emitter = setup_logging()

    database_manager = DatabaseManager(logger=logger)
    database_connection = database_manager.connect()
    logger.info(tr("startup.schema.ready"))

    apply_theme(app, config.get_theme(), logger)

    window = MainWindow(config=config, logger=logger, log_emitter=log_emitter, connection=database_connection)
    window.setWindowIcon(app_icon)
    window.theme_requested.connect(lambda theme: apply_theme(app, theme, logger))
    window.show()

    logger.info(tr("startup.ready"))

    app.aboutToQuit.connect(database_manager.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
