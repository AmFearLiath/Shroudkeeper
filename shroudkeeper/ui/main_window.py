from __future__ import annotations

import logging
from pathlib import Path
import sqlite3

from PySide6.QtCore import QEvent, QObject, Signal, Qt
from PySide6.QtGui import QCloseEvent, QFocusEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from core.automations.runner import AutomationRunner
from core.automations.scheduler import AutomationScheduler
from core.config import AppConfig
from core.logging import LogEmitter
from i18n.i18n import get_i18n, tr
from storage.repositories import AutomationJobRepository
from ui.components.ev_window_title_bar import EVWindowTitleBar
from ui.navigation import SidebarNavigation
from ui.views.automations_view import AutomationsView
from ui.views.backups_view import BackupsView
from ui.views.dashboard_view import DashboardView
from ui.views.server_view import ServerView
from ui.views.singleplayer_view import SingleplayerView
from ui.views.settings_view import SettingsView
from ui.views.transfers_view import TransfersView


class MainWindow(QMainWindow):
    theme_requested = Signal(str)
    _RESIZE_BORDER_PX = 8
    _NO_EDGE = Qt.Edge(0)

    def __init__(
        self,
        config: AppConfig,
        logger: logging.Logger,
        log_emitter: LogEmitter,
        connection: sqlite3.Connection,
    ) -> None:
        super().__init__()
        self._config = config
        self._logger = logger
        self._automation_runner = AutomationRunner(connection=connection, config=config, logger=logger)
        self._automation_scheduler = AutomationScheduler(repository=AutomationJobRepository(connection))
        self._automation_scheduler.job_due.connect(self._automation_runner.run_job_id)

        self._shell_widget: QWidget | None = None
        self._frameless_active = False
        self._active_resize_edges = self._NO_EDGE
        self._title_bar_offsets = {"right": 24, "top": 8}

        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self._central_widget = QWidget()
        self._central_widget.setObjectName("AppRoot")
        self.setCentralWidget(self._central_widget)

        self._central_layout = QVBoxLayout(self._central_widget)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)

        self._app_content = QWidget()
        self._app_content.setObjectName("AppContent")
        self._app_content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        app_layout = QVBoxLayout(self._app_content)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        self._title_bar = EVWindowTitleBar(self._central_widget)
        self._title_bar.minimize_requested.connect(self.showMinimized)
        self._title_bar.maximize_requested.connect(self.showMaximized)
        self._title_bar.restore_requested.connect(self.showNormal)
        self._title_bar.close_requested.connect(self.close)
        self._title_bar.setFixedWidth(210)
        self._title_bar.hide()

        body_row = QWidget()
        body_layout = QHBoxLayout(body_row)
        body_layout.setContentsMargins(0, 8, 0, 8)
        body_layout.setSpacing(12)
        app_layout.addWidget(body_row, 1)

        self._navigation = SidebarNavigation()
        body_layout.addWidget(self._navigation)

        right_container = QWidget()
        right_container.setObjectName("Content")
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self._stack = QStackedWidget()
        self._stack.setObjectName("ContentStack")
        self._stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        right_layout.addWidget(self._stack, 1)

        body_layout.addWidget(right_container, 1)

        self._views: dict[str, QWidget] = {
            "dashboard": DashboardView(),
            "singleplayer": SingleplayerView(
                singleplayer_root=self._config.get_singleplayer_root(),
                logger=self._logger,
            ),
            "server": ServerView(connection=connection, config=self._config, logger=self._logger),
            "transfers": TransfersView(connection=connection, config=self._config, logger=self._logger),
            "backups": BackupsView(connection=connection, config=self._config, logger=self._logger),
            "automations": AutomationsView(
                connection=connection,
                scheduler=self._automation_scheduler,
                runner=self._automation_runner,
                logger=self._logger,
            ),
            "settings": SettingsView(
                current_language=self._config.get_language(),
                current_theme=self._config.get_theme(),
                log_emitter=log_emitter,
            ),
        }

        singleplayer_view = self._views["singleplayer"]
        if isinstance(singleplayer_view, SingleplayerView):
            singleplayer_view.singleplayer_root_selected.connect(self._on_singleplayer_root_selected)

        for view in self._views.values():
            view.setObjectName("ContentView")
            view.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
            self._stack.addWidget(view)

        server_view = self._views.get("server")
        if isinstance(server_view, ServerView):
            server_view.profiles_changed.connect(self._on_profiles_changed)

        settings_view = self._views["settings"]
        if isinstance(settings_view, SettingsView):
            settings_view.language_selected.connect(self._on_language_selected)
            settings_view.theme_selected.connect(self._on_theme_selected)

        self._navigation.view_selected.connect(self._switch_view)
        get_i18n().language_changed.connect(self.retranslate_ui)

        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.applicationStateChanged.connect(self._on_application_state_changed)
            app.installEventFilter(self)

        self._apply_shell_for_theme(self._config.get_theme())

        self._switch_view("dashboard")
        self._navigation.select_view("dashboard", emit_signal=False)
        self.retranslate_ui()
        self._automation_scheduler.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._automation_scheduler.stop()
        super().closeEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if not self._frameless_active or self.isMaximized():
            return super().eventFilter(watched, event)

        if not isinstance(watched, QWidget):
            return super().eventFilter(watched, event)

        if watched is not self and not self.isAncestorOf(watched):
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent):
            edges = self._resize_edges_for_global_pos(event.globalPosition())
            self._active_resize_edges = edges
            self._update_resize_cursor(edges)
            return False

        if event.type() == QEvent.Type.Leave:
            self._active_resize_edges = self._NO_EDGE
            self.unsetCursor()
            return False

        if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
            if event.button() != Qt.MouseButton.LeftButton:
                return False

            edges = self._resize_edges_for_global_pos(event.globalPosition())
            if edges == self._NO_EDGE:
                return False

            handle = self.windowHandle()
            if handle is not None and handle.startSystemResize(edges):
                return True

        return super().eventFilter(watched, event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        self._sync_title_bar_state()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_title_bar()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        self._sync_title_bar_state()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        self._sync_title_bar_state()

    def _on_application_state_changed(self, _state: Qt.ApplicationState) -> None:
        self._sync_title_bar_state()

    def _sync_title_bar_state(self) -> None:
        self._title_bar.set_maximized(self.isMaximized())

    def _position_title_bar(self) -> None:
        if not self._title_bar.isVisible():
            return

        right_offset = int(self._title_bar_offsets.get("right", 24))
        top_offset = int(self._title_bar_offsets.get("top", 8))

        x = max(8, self._central_widget.width() - self._title_bar.width() - right_offset)
        y = max(0, top_offset)
        self._title_bar.move(x, y)
        self._title_bar.raise_()

    def _resize_edges_for_global_pos(self, global_pos) -> Qt.Edge:
        geometry = self.frameGeometry()
        x = int(global_pos.x())
        y = int(global_pos.y())
        margin = self._RESIZE_BORDER_PX

        edges = self._NO_EDGE
        if x <= geometry.left() + margin:
            edges |= Qt.Edge.LeftEdge
        elif x >= geometry.right() - margin:
            edges |= Qt.Edge.RightEdge

        if y <= geometry.top() + margin:
            edges |= Qt.Edge.TopEdge
        elif y >= geometry.bottom() - margin:
            edges |= Qt.Edge.BottomEdge

        return edges

    def _update_resize_cursor(self, edges: Qt.Edge) -> None:
        if edges in (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            return

        if edges in (Qt.Edge.RightEdge | Qt.Edge.TopEdge, Qt.Edge.LeftEdge | Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            return

        if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
            return

        if edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
            return

        self.unsetCursor()

    def _mount_app_content(self, host_widget: QWidget) -> None:
        self._app_content.setParent(None)

        host_layout = host_widget.layout()
        if host_layout is None:
            host_layout = QVBoxLayout(host_widget)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)

        host_layout.addWidget(self._app_content)

    def _clear_shell_widget(self) -> None:
        if self._shell_widget is None:
            return

        self._central_layout.removeWidget(self._shell_widget)
        self._shell_widget.setParent(None)
        self._shell_widget.deleteLater()
        self._shell_widget = None

    def _apply_shell_for_theme(self, _theme_setting: str) -> None:
        self._set_frameless_enabled(False)
        self._title_bar.hide()
        self._title_bar_offsets = {"right": 24, "top": 8}

        self._clear_shell_widget()

        shell = QWidget()
        shell.setObjectName("AppShell")
        self._mount_app_content(shell)
        self._shell_widget = shell
        self._central_layout.addWidget(shell)

    def _set_frameless_enabled(self, enabled: bool) -> None:
        if self._frameless_active == enabled:
            return

        self._frameless_active = enabled
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, enabled)
        if self.isVisible():
            self.show()

    def _switch_view(self, view_id: str) -> None:
        view = self._views.get(view_id)
        if view is None:
            return
        self._stack.setCurrentWidget(view)
        self._navigation.select_view(view_id, emit_signal=False)

    def _on_language_selected(self, language_code: str) -> None:
        self._config.set_language(language_code)
        get_i18n().set_language(language_code)
        language_name = tr(f"settings.language.{language_code}")
        self._logger.info(tr("startup.language.changed", language=language_name))

    def _on_theme_selected(self, theme_file: str) -> None:
        self._config.set_theme(theme_file)
        self.theme_requested.emit(theme_file)
        self._apply_shell_for_theme(theme_file)

    def _on_singleplayer_root_selected(self, root_path: str) -> None:
        normalized_root = str(Path(root_path).expanduser().resolve())
        self._config.set_singleplayer_root(normalized_root)

        opened_paths = self._config.get_last_opened_paths()
        if normalized_root not in opened_paths:
            opened_paths.append(normalized_root)
            self._config.set_last_opened_paths(opened_paths)

        singleplayer = self._views.get("singleplayer")
        if isinstance(singleplayer, SingleplayerView):
            singleplayer.set_scan_root(normalized_root)

        backups = self._views.get("backups")
        if isinstance(backups, BackupsView):
            backups.refresh_sources()

        transfers = self._views.get("transfers")
        if isinstance(transfers, TransfersView):
            transfers.refresh_sources()

        automations = self._views.get("automations")
        if isinstance(automations, AutomationsView):
            automations.refresh_profiles()

        self._logger.info(tr("startup.singleplayer_root.changed"))

    def _on_profiles_changed(self) -> None:
        backups = self._views.get("backups")
        if isinstance(backups, BackupsView):
            backups.refresh_sources()

        transfers = self._views.get("transfers")
        if isinstance(transfers, TransfersView):
            transfers.refresh_sources()

        automations = self._views.get("automations")
        if isinstance(automations, AutomationsView):
            automations.refresh_profiles()

    def retranslate_ui(self, _language: str | None = None) -> None:
        title = tr("app.window.title")
        self.setWindowTitle(title)
        self._title_bar.set_title(title)
