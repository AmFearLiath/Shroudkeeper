from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from __init__ import __version__
from core.resources import resource_path
from i18n.i18n import get_i18n, tr
from ui.components.ev_page_header import EVPageHeader


class DashboardView(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._header = EVPageHeader()
        layout.addWidget(self._header)

        self._hero_card = QWidget()
        self._hero_card.setObjectName("EVCard")
        hero_layout = QVBoxLayout(self._hero_card)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(10)

        self._tool_title = QLabel()
        self._tool_title.setObjectName("H1")
        self._tool_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tool_title.setStyleSheet("font-size: 38px; font-weight: 800;")
        hero_layout.addWidget(self._tool_title)

        self._meta_line = QLabel()
        self._meta_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self._meta_line)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_label.setMinimumHeight(300)
        hero_layout.addWidget(self._logo_label)

        layout.addWidget(self._hero_card)

        self._info_card = QWidget()
        self._info_card.setObjectName("EVCard")
        info_layout = QVBoxLayout(self._info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(10)

        self._info_title = QLabel()
        self._info_title.setObjectName("cardTitle")
        self._info_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self._info_title)

        self._info_manager = QLabel()
        self._info_manager.setWordWrap(True)
        self._info_manager.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(self._info_manager)

        self._info_savegames = QLabel()
        self._info_savegames.setWordWrap(True)
        self._info_savegames.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_savegames.hide()

        self._feature_singleplayer = QLabel()
        self._feature_singleplayer.setWordWrap(True)
        self._feature_singleplayer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_singleplayer.hide()

        self._feature_server = QLabel()
        self._feature_server.setWordWrap(True)
        self._feature_server.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_server.hide()

        self._feature_transfers = QLabel()
        self._feature_transfers.setWordWrap(True)
        self._feature_transfers.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_transfers.hide()

        self._feature_backups = QLabel()
        self._feature_backups.setWordWrap(True)
        self._feature_backups.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_backups.hide()

        self._feature_automations = QLabel()
        self._feature_automations.setWordWrap(True)
        self._feature_automations.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_automations.hide()

        self._feature_settings = QLabel()
        self._feature_settings.setWordWrap(True)
        self._feature_settings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feature_settings.hide()

        layout.addWidget(self._info_card)

        self._links_card = QWidget()
        self._links_card.setObjectName("EVCard")
        links_layout = QHBoxLayout(self._links_card)
        links_layout.setContentsMargins(16, 12, 16, 12)
        links_layout.setSpacing(10)

        self._footer_meta = QLabel()
        self._footer_meta.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        links_layout.addWidget(self._footer_meta, 0)

        links_layout.addStretch(1)

        self._discord_link = QLabel()
        self._discord_link.setOpenExternalLinks(True)
        self._discord_link.setTextFormat(Qt.TextFormat.RichText)
        self._discord_link.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        links_layout.addWidget(self._discord_link, 0)

        self._footer_link_sep = QLabel("·")
        self._footer_link_sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        links_layout.addWidget(self._footer_link_sep, 0)

        self._github_placeholder = QLabel()
        self._github_placeholder.setOpenExternalLinks(True)
        self._github_placeholder.setTextFormat(Qt.TextFormat.RichText)
        self._github_placeholder.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._github_placeholder.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        links_layout.addWidget(self._github_placeholder, 0)

        layout.addWidget(self._links_card)
        layout.addStretch(1)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _update_logo(self) -> None:
        logo_path = resource_path("assets/images/logo.png")
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            self._logo_label.clear()
            return

        preferred_width = max(760, self.width() - 340)
        scaled = pixmap.scaledToWidth(preferred_width, Qt.TransformationMode.SmoothTransformation)
        self._logo_label.setPixmap(scaled)

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("dashboard.title"))
        self._tool_title.setText(tr("dashboard.meta.tool_title"))
        self._meta_line.setText(tr("dashboard.meta.tagline"))
        self._footer_meta.setText(
            tr("dashboard.meta.author") + " · " + tr("dashboard.meta.version", version=__version__)
        )
        self._discord_link.setText(tr("dashboard.meta.discord"))
        self._github_placeholder.setText(tr("dashboard.meta.github"))

        self._update_logo()

        self._info_title.setText(tr("dashboard.info.title"))
        self._info_manager.setText(tr("dashboard.info.disclaimer"))
        self._info_savegames.clear()
        self._feature_singleplayer.clear()
        self._feature_server.clear()
        self._feature_transfers.clear()
        self._feature_backups.clear()
        self._feature_automations.clear()
        self._feature_settings.clear()
