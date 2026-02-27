from __future__ import annotations

import json

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from i18n.i18n import tr
from ui.components.ev_card import EVCard


class MultiplayerConfigDialog(QDialog):
    def __init__(self, profile_name: str, remote_path: str, payload: dict[str, object], parent=None) -> None:
        super().__init__(parent)
        self._profile_name = profile_name
        self._remote_path = remote_path
        self._payload = payload
        self._sync_lock = False

        self.setModal(True)
        self.setMinimumSize(980, 640)
        self.resize(1080, 760)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._headline = QLabel()
        self._headline.setObjectName("viewHeadline")
        layout.addWidget(self._headline)

        self._path_label = QLabel()
        self._path_label.setObjectName("infoBar")
        layout.addWidget(self._path_label)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        form_tab = self._build_form_tab()
        json_tab = self._build_json_tab()
        self._tabs.addTab(form_tab, tr("multiplayer.config.tab.form"))
        self._tabs.addTab(json_tab, tr("multiplayer.config.tab.json"))

        buttons = QHBoxLayout()
        self._footer_hint = QLabel()
        self._footer_hint.setObjectName("mutedLabel")
        buttons.addWidget(self._footer_hint)
        buttons.addStretch(1)
        self._cancel_button = QPushButton(tr("common.cancel"))
        self._cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self._cancel_button)
        self._save_button = QPushButton(tr("common.save"))
        self._save_button.setObjectName("primaryButton")
        self._save_button.clicked.connect(self._save)
        buttons.addWidget(self._save_button)
        layout.addLayout(buttons)

        self._retranslate()
        self._load_form_from_payload()
        self._sync_json_from_form()
        self._wire_form_autosync()
        self._json_editor.textChanged.connect(self._on_json_changed)

        self._known_tags = [
            "PVE",
            "PVP",
            "Roleplay",
            "Casual",
            "Hardcore",
            "German",
            "English",
            "EU",
            "US",
            "Modded",
            "Vanilla",
            "BeginnerFriendly",
        ]
        self._tag_completer = QCompleter(self._known_tags, self)
        self._tag_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._tag_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._tag_completer.activated.connect(self._insert_tag_completion)
        self._tags.setCompleter(self._tag_completer)
        self._tags.installEventFilter(self)

    def _build_form_tab(self):
        host = QWidget()
        host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        container = QVBoxLayout(content)
        container.setContentsMargins(8, 8, 8, 8)
        container.setSpacing(12)

        basic_card = EVCard()
        basic_layout = basic_card.body_layout()
        self._section_basic = QLabel()
        self._section_basic.setObjectName("cardTitle")
        basic_layout.addWidget(self._section_basic)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)

        self._name = QLineEdit()
        form.addRow(tr("multiplayer.config.name"), self._name)

        self._save_directory = QLineEdit()
        form.addRow(tr("multiplayer.config.save_dir"), self._save_directory)

        self._log_directory = QLineEdit()
        form.addRow(tr("multiplayer.config.log_dir"), self._log_directory)

        self._ip = QLineEdit()
        form.addRow(tr("multiplayer.config.ip"), self._ip)

        self._query_port = QSpinBox()
        self._query_port.setRange(1, 65535)
        form.addRow(tr("multiplayer.config.query_port"), self._query_port)

        self._slot_count = QSpinBox()
        self._slot_count.setRange(1, 16)
        form.addRow(tr("multiplayer.config.slot_count"), self._slot_count)

        basic_layout.addLayout(form)
        container.addWidget(basic_card)

        chat_card = EVCard()
        chat_layout = chat_card.body_layout()
        self._section_chat = QLabel()
        self._section_chat.setObjectName("cardTitle")
        chat_layout.addWidget(self._section_chat)

        chat_form = QFormLayout()
        chat_form.setHorizontalSpacing(14)
        chat_form.setVerticalSpacing(10)

        self._voice_chat_mode = QComboBox()
        self._voice_chat_mode.addItems(["Proximity", "Global"])
        chat_form.addRow(tr("multiplayer.config.voice_mode"), self._voice_chat_mode)

        self._enable_voice = QCheckBox()
        chat_form.addRow(tr("multiplayer.config.enable_voice"), self._enable_voice)

        self._enable_text = QCheckBox()
        chat_form.addRow(tr("multiplayer.config.enable_text"), self._enable_text)

        chat_layout.addLayout(chat_form)
        container.addWidget(chat_card)

        permissions_card = EVCard()
        permissions_layout = permissions_card.body_layout()
        self._section_permissions = QLabel()
        self._section_permissions.setObjectName("cardTitle")

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.addWidget(self._section_permissions, 1)
        self._add_usergroup = QPushButton("+")
        self._add_usergroup.setToolTip(tr("multiplayer.config.usergroups.add"))
        self._add_usergroup.setFixedWidth(30)
        self._add_usergroup.clicked.connect(self._add_usergroup_row)
        header_row.addWidget(self._add_usergroup, 0)
        permissions_layout.addLayout(header_row)

        self._usergroups_table = QTableWidget(0, 9)
        self._usergroups_table.setObjectName("EVTable")
        self._usergroups_table.verticalHeader().setVisible(False)
        self._usergroups_table.setAlternatingRowColors(True)
        self._usergroups_table.setMinimumHeight(220)
        self._usergroups_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self._usergroups_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5, 6, 7, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._usergroups_table.setHorizontalHeaderLabels(
            [
                tr("multiplayer.config.usergroups.name"),
                tr("multiplayer.config.usergroups.password"),
                tr("multiplayer.config.usergroups.kickban"),
                tr("multiplayer.config.usergroups.inventories"),
                tr("multiplayer.config.usergroups.editworld"),
                tr("multiplayer.config.usergroups.editbase"),
                tr("multiplayer.config.usergroups.extendbase"),
                tr("multiplayer.config.usergroups.reserved"),
                tr("multiplayer.config.usergroups.actions"),
            ]
        )
        permissions_layout.addWidget(self._usergroups_table)
        container.addWidget(permissions_card)

        gamesettings_card = EVCard()
        gamesettings_layout = gamesettings_card.body_layout()
        self._section_gamesettings = QLabel()
        self._section_gamesettings.setObjectName("cardTitle")
        gamesettings_layout.addWidget(self._section_gamesettings)

        game_form = QFormLayout()
        game_form.setHorizontalSpacing(14)
        game_form.setVerticalSpacing(10)

        self._preset = QComboBox()
        self._preset.addItems(["Default", "Relaxed", "Hard", "Survival", "Custom"])
        game_form.addRow(self._setting_label(tr("multiplayer.config.preset"), tr("multiplayer.config.tip.preset")), self._preset)

        self._game_settings_hint = QLabel(tr("multiplayer.config.hint.custom_required"))
        self._game_settings_hint.setObjectName("infoBar")
        gamesettings_layout.addWidget(self._game_settings_hint)

        self._tags = QLineEdit()
        game_form.addRow(self._setting_label(tr("multiplayer.config.tags"), tr("multiplayer.config.tip.tags")), self._tags)

        self._player_health = QDoubleSpinBox()
        self._player_health.setRange(0.25, 4.0)
        self._player_health.setSingleStep(0.25)
        self._player_health_control = self._numeric_slider_control(self._player_health)
        game_form.addRow(self._setting_label(tr("multiplayer.config.player_health"), tr("multiplayer.config.tip.player_health")), self._player_health_control)

        self._player_mana = QDoubleSpinBox()
        self._player_mana.setRange(0.25, 4.0)
        self._player_mana.setSingleStep(0.25)
        self._player_mana_control = self._numeric_slider_control(self._player_mana)
        game_form.addRow(self._setting_label(tr("multiplayer.config.player_mana"), tr("multiplayer.config.tip.player_mana")), self._player_mana_control)

        self._player_stamina = QDoubleSpinBox()
        self._player_stamina.setRange(0.25, 4.0)
        self._player_stamina.setSingleStep(0.25)
        self._player_stamina_control = self._numeric_slider_control(self._player_stamina)
        game_form.addRow(self._setting_label(tr("multiplayer.config.player_stamina"), tr("multiplayer.config.tip.player_stamina")), self._player_stamina_control)

        self._body_heat = QDoubleSpinBox()
        self._body_heat.setRange(0.5, 2.0)
        self._body_heat.setSingleStep(0.1)
        self._body_heat_control = self._numeric_slider_control(self._body_heat)
        game_form.addRow(self._setting_label(tr("multiplayer.config.body_heat"), tr("multiplayer.config.tip.body_heat")), self._body_heat_control)

        self._diving_time = QDoubleSpinBox()
        self._diving_time.setRange(0.5, 2.0)
        self._diving_time.setSingleStep(0.1)
        self._diving_time_control = self._numeric_slider_control(self._diving_time)
        game_form.addRow(self._setting_label(tr("multiplayer.config.diving_time"), tr("multiplayer.config.tip.diving_time")), self._diving_time_control)

        self._enable_durability = QCheckBox()
        game_form.addRow(self._setting_label(tr("multiplayer.config.enable_durability"), tr("multiplayer.config.tip.enable_durability")), self._enable_durability)

        self._enable_starving = QCheckBox()
        game_form.addRow(self._setting_label(tr("multiplayer.config.enable_starving"), tr("multiplayer.config.tip.enable_starving")), self._enable_starving)

        self._food_buff_duration = QDoubleSpinBox()
        self._food_buff_duration.setRange(0.5, 2.0)
        self._food_buff_duration.setSingleStep(0.1)
        self._food_buff_duration_control = self._numeric_slider_control(self._food_buff_duration)
        game_form.addRow(self._setting_label(tr("multiplayer.config.food_buff_duration"), tr("multiplayer.config.tip.food_buff_duration")), self._food_buff_duration_control)

        self._shroud_time = QDoubleSpinBox()
        self._shroud_time.setRange(0.5, 2.0)
        self._shroud_time.setSingleStep(0.1)
        self._shroud_time_control = self._numeric_slider_control(self._shroud_time)
        game_form.addRow(self._setting_label(tr("multiplayer.config.shroud_time"), tr("multiplayer.config.tip.shroud_time")), self._shroud_time_control)

        self._enemy_damage = QDoubleSpinBox()
        self._enemy_damage.setRange(0.25, 5.0)
        self._enemy_damage.setSingleStep(0.25)
        self._enemy_damage_control = self._numeric_slider_control(self._enemy_damage)
        game_form.addRow(self._setting_label(tr("multiplayer.config.enemy_damage"), tr("multiplayer.config.tip.enemy_damage")), self._enemy_damage_control)

        self._enemy_health = QDoubleSpinBox()
        self._enemy_health.setRange(0.25, 4.0)
        self._enemy_health.setSingleStep(0.25)
        self._enemy_health_control = self._numeric_slider_control(self._enemy_health)
        game_form.addRow(self._setting_label(tr("multiplayer.config.enemy_health"), tr("multiplayer.config.tip.enemy_health")), self._enemy_health_control)

        self._boss_damage = QDoubleSpinBox()
        self._boss_damage.setRange(0.2, 5.0)
        self._boss_damage.setSingleStep(0.1)
        self._boss_damage_control = self._numeric_slider_control(self._boss_damage)
        game_form.addRow(self._setting_label(tr("multiplayer.config.boss_damage"), tr("multiplayer.config.tip.boss_damage")), self._boss_damage_control)

        self._boss_health = QDoubleSpinBox()
        self._boss_health.setRange(0.2, 5.0)
        self._boss_health.setSingleStep(0.1)
        self._boss_health_control = self._numeric_slider_control(self._boss_health)
        game_form.addRow(self._setting_label(tr("multiplayer.config.boss_health"), tr("multiplayer.config.tip.boss_health")), self._boss_health_control)

        self._mining_damage = QDoubleSpinBox()
        self._mining_damage.setRange(0.5, 2.0)
        self._mining_damage.setSingleStep(0.1)
        self._mining_damage_control = self._numeric_slider_control(self._mining_damage)
        game_form.addRow(self._setting_label(tr("multiplayer.config.mining_damage"), tr("multiplayer.config.tip.mining_damage")), self._mining_damage_control)

        self._resource_drop = QDoubleSpinBox()
        self._resource_drop.setRange(0.25, 2.0)
        self._resource_drop.setSingleStep(0.1)
        self._resource_drop_control = self._numeric_slider_control(self._resource_drop)
        game_form.addRow(self._setting_label(tr("multiplayer.config.resource_drop"), tr("multiplayer.config.tip.resource_drop")), self._resource_drop_control)

        self._factory_speed = QDoubleSpinBox()
        self._factory_speed.setRange(0.25, 2.0)
        self._factory_speed.setSingleStep(0.1)
        self._factory_speed_control = self._numeric_slider_control(self._factory_speed)
        game_form.addRow(self._setting_label("Factory Speed (0.25-2)", tr("multiplayer.config.tip.factory_speed")), self._factory_speed_control)

        self._recycling_factor = QDoubleSpinBox()
        self._recycling_factor.setRange(0.0, 1.0)
        self._recycling_factor.setSingleStep(0.05)
        self._recycling_factor_control = self._numeric_slider_control(self._recycling_factor)
        game_form.addRow(self._setting_label("Recycling Factor (0-1)", tr("multiplayer.config.tip.recycling_factor")), self._recycling_factor_control)

        self._perk_cost = QDoubleSpinBox()
        self._perk_cost.setRange(0.25, 2.0)
        self._perk_cost.setSingleStep(0.1)
        self._perk_cost_control = self._numeric_slider_control(self._perk_cost)
        game_form.addRow(self._setting_label("Perk Cost (0.25-2)", tr("multiplayer.config.tip.perk_cost")), self._perk_cost_control)

        self._xp_combat = QDoubleSpinBox()
        self._xp_combat.setRange(0.25, 2.0)
        self._xp_combat.setSingleStep(0.1)
        self._xp_combat_control = self._numeric_slider_control(self._xp_combat)
        game_form.addRow(self._setting_label("XP Combat (0.25-2)", tr("multiplayer.config.tip.xp_combat")), self._xp_combat_control)

        self._xp_mining = QDoubleSpinBox()
        self._xp_mining.setRange(0.0, 2.0)
        self._xp_mining.setSingleStep(0.1)
        self._xp_mining_control = self._numeric_slider_control(self._xp_mining)
        game_form.addRow(self._setting_label("XP Mining (0-2)", tr("multiplayer.config.tip.xp_mining")), self._xp_mining_control)

        self._xp_exploration = QDoubleSpinBox()
        self._xp_exploration.setRange(0.25, 2.0)
        self._xp_exploration.setSingleStep(0.1)
        self._xp_exploration_control = self._numeric_slider_control(self._xp_exploration)
        game_form.addRow(self._setting_label("XP Exploration (0.25-2)", tr("multiplayer.config.tip.xp_exploration")), self._xp_exploration_control)

        self._enemy_stamina = QDoubleSpinBox()
        self._enemy_stamina.setRange(0.5, 2.0)
        self._enemy_stamina.setSingleStep(0.1)
        self._enemy_stamina_control = self._numeric_slider_control(self._enemy_stamina)
        game_form.addRow(self._setting_label("Enemy Stamina (0.5-2)", tr("multiplayer.config.tip.enemy_stamina")), self._enemy_stamina_control)

        self._enemy_perception = QDoubleSpinBox()
        self._enemy_perception.setRange(0.5, 2.0)
        self._enemy_perception.setSingleStep(0.1)
        self._enemy_perception_control = self._numeric_slider_control(self._enemy_perception)
        game_form.addRow(self._setting_label("Enemy Perception (0.5-2)", tr("multiplayer.config.tip.enemy_perception")), self._enemy_perception_control)

        self._threat_bonus = QDoubleSpinBox()
        self._threat_bonus.setRange(0.25, 4.0)
        self._threat_bonus.setSingleStep(0.1)
        self._threat_bonus_control = self._numeric_slider_control(self._threat_bonus)
        game_form.addRow(self._setting_label("Threat Bonus (0.25-4)", tr("multiplayer.config.tip.threat_bonus")), self._threat_bonus_control)

        self._plant_growth = QDoubleSpinBox()
        self._plant_growth.setRange(0.25, 2.0)
        self._plant_growth.setSingleStep(0.1)
        self._plant_growth_control = self._numeric_slider_control(self._plant_growth)
        game_form.addRow(self._setting_label("Plant Growth (0.25-2)", tr("multiplayer.config.tip.plant_growth")), self._plant_growth_control)

        self._from_hunger_seconds = QSpinBox()
        self._from_hunger_seconds.setRange(300, 1200)
        self._from_hunger_seconds_control = self._numeric_slider_control(self._from_hunger_seconds)
        game_form.addRow(self._setting_label("Hungry->Starving (s)", tr("multiplayer.config.tip.from_hunger")), self._from_hunger_seconds_control)

        self._day_time_seconds = QSpinBox()
        self._day_time_seconds.setRange(120, 3600)
        self._day_time_seconds_control = self._numeric_slider_control(self._day_time_seconds)
        game_form.addRow(self._setting_label("Day Time (s)", tr("multiplayer.config.tip.day_time")), self._day_time_seconds_control)

        self._night_time_seconds = QSpinBox()
        self._night_time_seconds.setRange(120, 3600)
        self._night_time_seconds_control = self._numeric_slider_control(self._night_time_seconds)
        game_form.addRow(self._setting_label("Night Time (s)", tr("multiplayer.config.tip.night_time")), self._night_time_seconds_control)

        self._weather_frequency = QComboBox()
        self._weather_frequency.addItems(["Disabled", "Rare", "Normal", "Often"])
        game_form.addRow(self._setting_label("Weather Frequency", tr("multiplayer.config.tip.weather_frequency")), self._weather_frequency)

        self._fishing_difficulty = QComboBox()
        self._fishing_difficulty.addItems(["VeryEasy", "Easy", "Normal", "Hard", "VeryHard"])
        game_form.addRow(self._setting_label("Fishing Difficulty", tr("multiplayer.config.tip.fishing_difficulty")), self._fishing_difficulty)

        self._random_spawner_amount = QComboBox()
        self._random_spawner_amount.addItems(["Few", "Normal", "Many", "Extreme"])
        game_form.addRow(self._setting_label("Enemy Amount", tr("multiplayer.config.tip.enemy_amount")), self._random_spawner_amount)

        self._aggro_pool_amount = QComboBox()
        self._aggro_pool_amount.addItems(["Few", "Normal", "Many", "Extreme"])
        game_form.addRow(self._setting_label("Aggro Pool", tr("multiplayer.config.tip.aggro_pool")), self._aggro_pool_amount)

        self._tombstone_mode = QComboBox()
        self._tombstone_mode.addItems(["AddBackpackMaterials", "Everything", "NoTombstone"])
        game_form.addRow(self._setting_label("Tombstone Mode", tr("multiplayer.config.tip.tombstone_mode")), self._tombstone_mode)

        self._curse_modifier = QComboBox()
        self._curse_modifier.addItems(["Easy", "Normal", "Hard"])
        game_form.addRow(self._setting_label("Curse Modifier", tr("multiplayer.config.tip.curse_modifier")), self._curse_modifier)

        self._taming_repercussion = QComboBox()
        self._taming_repercussion.addItems(["KeepProgress", "LoseSomeProgress", "LoseAllProgress"])
        game_form.addRow(self._setting_label("Taming Repercussion", tr("multiplayer.config.tip.taming_repercussion")), self._taming_repercussion)

        self._pacify_enemies = QCheckBox()
        game_form.addRow(self._setting_label("Pacify All Enemies", tr("multiplayer.config.tip.pacify_enemies")), self._pacify_enemies)

        self._glider_turbulence = QCheckBox()
        game_form.addRow(self._setting_label("Enable Glider Turbulence", tr("multiplayer.config.tip.glider_turbulence")), self._glider_turbulence)

        gamesettings_layout.addLayout(game_form)
        container.addWidget(gamesettings_card)

        self._game_setting_widgets = [
            self._tags,
            self._player_health_control,
            self._player_mana_control,
            self._player_stamina_control,
            self._body_heat_control,
            self._diving_time_control,
            self._enable_durability,
            self._enable_starving,
            self._food_buff_duration_control,
            self._shroud_time_control,
            self._enemy_damage_control,
            self._enemy_health_control,
            self._boss_damage_control,
            self._boss_health_control,
            self._mining_damage_control,
            self._resource_drop_control,
            self._factory_speed_control,
            self._recycling_factor_control,
            self._perk_cost_control,
            self._xp_combat_control,
            self._xp_mining_control,
            self._xp_exploration_control,
            self._enemy_stamina_control,
            self._enemy_perception_control,
            self._threat_bonus_control,
            self._plant_growth_control,
            self._from_hunger_seconds_control,
            self._day_time_seconds_control,
            self._night_time_seconds_control,
            self._weather_frequency,
            self._fishing_difficulty,
            self._random_spawner_amount,
            self._aggro_pool_amount,
            self._tombstone_mode,
            self._curse_modifier,
            self._taming_repercussion,
            self._pacify_enemies,
            self._glider_turbulence,
        ]
        self._preset.currentTextChanged.connect(self._update_game_settings_enabled)
        self._update_game_settings_enabled()

        bans_card = EVCard()
        bans_layout = bans_card.body_layout()
        self._section_bans = QLabel(tr("multiplayer.config.section.bans"))
        self._section_bans.setObjectName("cardTitle")
        bans_layout.addWidget(self._section_bans)

        self._ban_info = QLabel(tr("multiplayer.config.bans.info"))
        self._ban_info.setObjectName("mutedLabel")
        bans_layout.addWidget(self._ban_info)

        self._bans_table = QTableWidget(0, 3)
        self._bans_table.setObjectName("EVTable")
        self._bans_table.verticalHeader().setVisible(False)
        self._bans_table.setAlternatingRowColors(True)
        bans_header = self._bans_table.horizontalHeader()
        bans_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        bans_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        bans_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._bans_table.setHorizontalHeaderLabels(
            [
                tr("multiplayer.config.bans.id"),
                tr("multiplayer.config.bans.name"),
                tr("multiplayer.config.usergroups.actions"),
            ]
        )
        bans_layout.addWidget(self._bans_table)

        ban_tools = QHBoxLayout()
        ban_tools.addStretch(1)
        self._add_ban_button = QPushButton("+")
        self._add_ban_button.setToolTip(tr("multiplayer.config.bans.add"))
        self._add_ban_button.setFixedWidth(30)
        self._add_ban_button.clicked.connect(self._add_ban_row)
        ban_tools.addWidget(self._add_ban_button)
        bans_layout.addLayout(ban_tools)
        container.addWidget(bans_card)

        container.addStretch(1)
        scroll.setWidget(content)
        host_layout.addWidget(scroll, 1)

        return host

    def _setting_label(self, text: str, tooltip: str) -> QWidget:
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        info_label = QLabel("ⓘ")
        info_label.setToolTip(tooltip)
        info_label.setObjectName("mutedLabel")
        row.addWidget(info_label)

        text_label = QLabel(text)
        row.addWidget(text_label)
        row.addStretch(1)
        return host

    def _numeric_slider_control(self, spinbox: QSpinBox | QDoubleSpinBox) -> QWidget:
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        slider.setSingleStep(1)
        slider.setPageStep(1)

        value_input = QLineEdit()
        value_input.setMinimumWidth(70)
        value_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        if isinstance(spinbox, QDoubleSpinBox):
            step = spinbox.singleStep()
            scale = max(1, int(round(1.0 / step)))
            minimum = int(round(spinbox.minimum() * scale))
            maximum = int(round(spinbox.maximum() * scale))
            slider.setRange(minimum, maximum)
            decimals = max(0, len(str(step).split(".")[1].rstrip("0")) if "." in str(step) else 0)
            validator = QDoubleValidator(spinbox.minimum(), spinbox.maximum(), max(1, decimals), value_input)
            value_input.setValidator(validator)

            def _on_slider_changed(value: int) -> None:
                float_value = value / scale
                if abs(spinbox.value() - float_value) > 1e-6:
                    spinbox.setValue(float_value)
                value_input.setText(f"{float_value:.2f}".rstrip("0").rstrip("."))

            def _on_spin_changed(value: float) -> None:
                slider_value = int(round(value * scale))
                if slider.value() != slider_value:
                    slider.setValue(slider_value)
                value_input.setText(f"{value:.2f}".rstrip("0").rstrip("."))

            def _on_input_finished() -> None:
                raw = value_input.text().strip().replace(",", ".")
                if raw == "":
                    _on_spin_changed(spinbox.value())
                    return
                try:
                    parsed = float(raw)
                except ValueError:
                    _on_spin_changed(spinbox.value())
                    return
                parsed = max(spinbox.minimum(), min(spinbox.maximum(), parsed))
                spinbox.setValue(parsed)

            slider.valueChanged.connect(_on_slider_changed)
            spinbox.valueChanged.connect(_on_spin_changed)
            value_input.editingFinished.connect(_on_input_finished)
            slider.setValue(int(round(spinbox.value() * scale)))
            _on_spin_changed(spinbox.value())
        else:
            slider.setRange(spinbox.minimum(), spinbox.maximum())
            value_input.setValidator(QIntValidator(spinbox.minimum(), spinbox.maximum(), value_input))

            def _on_slider_changed(value: int) -> None:
                if spinbox.value() != value:
                    spinbox.setValue(value)
                value_input.setText(str(value))

            def _on_spin_changed(value: int) -> None:
                if slider.value() != value:
                    slider.setValue(value)
                value_input.setText(str(value))

            def _on_input_finished() -> None:
                raw = value_input.text().strip()
                if raw == "":
                    _on_spin_changed(spinbox.value())
                    return
                try:
                    parsed = int(raw)
                except ValueError:
                    _on_spin_changed(spinbox.value())
                    return
                parsed = max(spinbox.minimum(), min(spinbox.maximum(), parsed))
                spinbox.setValue(parsed)

            slider.valueChanged.connect(_on_slider_changed)
            spinbox.valueChanged.connect(_on_spin_changed)
            value_input.editingFinished.connect(_on_input_finished)
            slider.setValue(spinbox.value())
            _on_spin_changed(spinbox.value())

        spinbox.setVisible(False)
        row.addWidget(slider, 1)
        row.addWidget(value_input, 0)
        return host

    def eventFilter(self, obj, event):
        if obj is self._tags and event.type() == QEvent.Type.FocusIn:
            if self._tag_completer is not None:
                self._tag_completer.setCompletionPrefix("")
                self._tag_completer.complete()
        return super().eventFilter(obj, event)

    def _build_json_tab(self):
        host = QWidget()
        container = QVBoxLayout(host)
        container.setContentsMargins(8, 8, 8, 8)
        container.setSpacing(8)

        self._json_editor = QTextEdit()
        self._json_editor.setObjectName("EVCodeEditor")
        container.addWidget(self._json_editor, 1)
        return host

    def _update_game_settings_enabled(self) -> None:
        is_custom = self._preset.currentText() == "Custom"
        for widget in self._game_setting_widgets:
            widget.setEnabled(is_custom)
        self._game_settings_hint.setVisible(not is_custom)

    def _load_form_from_payload(self) -> None:
        payload = self._payload
        game_settings = payload.get("gameSettings") if isinstance(payload.get("gameSettings"), dict) else {}

        self._sync_lock = True

        self._name.setText(str(payload.get("name", "Enshrouded Server")))
        self._save_directory.setText(str(payload.get("saveDirectory", "./savegame")))
        self._log_directory.setText(str(payload.get("logDirectory", "./logs")))
        self._ip.setText(str(payload.get("ip", "0.0.0.0")))
        self._query_port.setValue(int(payload.get("queryPort", 15637)))
        self._slot_count.setValue(int(payload.get("slotCount", 16)))

        voice_mode = str(payload.get("voiceChatMode", "Proximity"))
        self._voice_chat_mode.setCurrentText(voice_mode if voice_mode in {"Proximity", "Global"} else "Proximity")

        self._enable_voice.setChecked(bool(payload.get("enableVoiceChat", False)))
        self._enable_text.setChecked(bool(payload.get("enableTextChat", False)))

        preset = str(payload.get("gameSettingsPreset", "Default"))
        self._preset.setCurrentText(preset if preset in {"Default", "Relaxed", "Hard", "Survival", "Custom"} else "Default")

        tags = payload.get("tags", [])
        if isinstance(tags, list):
            self._tags.setText(", ".join(str(item) for item in tags if isinstance(item, str)))
        else:
            self._tags.setText("")

        self._player_health.setValue(float(game_settings.get("playerHealthFactor", 1.0)))
        self._player_mana.setValue(float(game_settings.get("playerManaFactor", 1.0)))
        self._player_stamina.setValue(float(game_settings.get("playerStaminaFactor", 1.0)))
        self._body_heat.setValue(float(game_settings.get("playerBodyHeatFactor", 1.0)))
        self._diving_time.setValue(float(game_settings.get("playerDivingTimeFactor", 1.0)))
        self._enable_durability.setChecked(bool(game_settings.get("enableDurability", True)))
        self._enable_starving.setChecked(bool(game_settings.get("enableStarvingDebuff", False)))
        self._food_buff_duration.setValue(float(game_settings.get("foodBuffDurationFactor", 1.0)))
        self._shroud_time.setValue(float(game_settings.get("shroudTimeFactor", 1.0)))
        self._enemy_damage.setValue(float(game_settings.get("enemyDamageFactor", 1.0)))
        self._enemy_health.setValue(float(game_settings.get("enemyHealthFactor", 1.0)))
        self._boss_damage.setValue(float(game_settings.get("bossDamageFactor", 1.0)))
        self._boss_health.setValue(float(game_settings.get("bossHealthFactor", 1.0)))
        self._mining_damage.setValue(float(game_settings.get("miningDamageFactor", 1.0)))
        self._resource_drop.setValue(float(game_settings.get("resourceDropStackAmountFactor", 1.0)))
        self._factory_speed.setValue(float(game_settings.get("factoryProductionSpeedFactor", 1.0)))
        self._recycling_factor.setValue(float(game_settings.get("perkUpgradeRecyclingFactor", 0.5)))
        self._perk_cost.setValue(float(game_settings.get("perkCostFactor", 1.0)))
        self._xp_combat.setValue(float(game_settings.get("experienceCombatFactor", 1.0)))
        self._xp_mining.setValue(float(game_settings.get("experienceMiningFactor", 1.0)))
        self._xp_exploration.setValue(float(game_settings.get("experienceExplorationQuestsFactor", 1.0)))
        self._enemy_stamina.setValue(float(game_settings.get("enemyStaminaFactor", 1.0)))
        self._enemy_perception.setValue(float(game_settings.get("enemyPerceptionRangeFactor", 1.0)))
        self._threat_bonus.setValue(float(game_settings.get("threatBonus", 1.0)))
        self._plant_growth.setValue(float(game_settings.get("plantGrowthSpeedFactor", 1.0)))
        self._from_hunger_seconds.setValue(int(int(game_settings.get("fromHungerToStarving", 600_000_000_000)) / 1_000_000_000))
        self._day_time_seconds.setValue(int(int(game_settings.get("dayTimeDuration", 1_800_000_000_000)) / 1_000_000_000))
        self._night_time_seconds.setValue(int(int(game_settings.get("nightTimeDuration", 720_000_000_000)) / 1_000_000_000))

        self._weather_frequency.setCurrentText(str(game_settings.get("weatherFrequency", "Normal")))
        self._fishing_difficulty.setCurrentText(str(game_settings.get("fishingDifficulty", "Normal")))
        self._random_spawner_amount.setCurrentText(str(game_settings.get("randomSpawnerAmount", "Normal")))
        self._aggro_pool_amount.setCurrentText(str(game_settings.get("aggroPoolAmount", "Normal")))
        self._tombstone_mode.setCurrentText(str(game_settings.get("tombstoneMode", "AddBackpackMaterials")))
        self._curse_modifier.setCurrentText(str(game_settings.get("curseModifier", "Normal")))
        self._taming_repercussion.setCurrentText(str(game_settings.get("tamingStartleRepercussion", "LoseSomeProgress")))
        self._pacify_enemies.setChecked(bool(game_settings.get("pacifyAllEnemies", False)))
        self._glider_turbulence.setChecked(bool(game_settings.get("enableGliderTurbulences", True)))

        self._load_usergroups(payload)
        self._load_bans(payload)

        self._sync_lock = False

    def _load_usergroups(self, payload: dict[str, object]) -> None:
        self._usergroups_table.setRowCount(0)
        groups = payload.get("userGroups")
        if not isinstance(groups, list):
            return
        for group in groups:
            if not isinstance(group, dict):
                continue
            self._add_usergroup_row(
                name=str(group.get("name", "")),
                password=str(group.get("password", "")),
                can_kick_ban=bool(group.get("canKickBan", False)),
                can_access=bool(group.get("canAccessInventories", False)),
                can_edit_world=bool(group.get("canEditWorld", False)),
                can_edit_base=bool(group.get("canEditBase", False)),
                can_extend_base=bool(group.get("canExtendBase", False)),
                reserved_slots=int(group.get("reservedSlots", 0)),
            )

    def _add_usergroup_row(
        self,
        name: str = "",
        password: str = "",
        can_kick_ban: bool = False,
        can_access: bool = False,
        can_edit_world: bool = False,
        can_edit_base: bool = False,
        can_extend_base: bool = False,
        reserved_slots: int = 0,
    ) -> None:
        row = self._usergroups_table.rowCount()
        self._usergroups_table.insertRow(row)

        self._usergroups_table.setItem(row, 0, QTableWidgetItem(name))
        self._usergroups_table.setItem(row, 1, QTableWidgetItem(password))

        for col, checked in ((2, can_kick_ban), (3, can_access), (4, can_edit_world), (5, can_edit_base), (6, can_extend_base)):
            checkbox = QCheckBox()
            checkbox.setChecked(checked)
            checkbox.setStyleSheet("margin-left: 8px;")
            checkbox.stateChanged.connect(self._on_form_changed)
            self._usergroups_table.setCellWidget(row, col, checkbox)

        reserved = QSpinBox()
        reserved.setRange(0, 16)
        reserved.setValue(max(0, min(16, int(reserved_slots))))
        reserved.valueChanged.connect(self._on_form_changed)
        self._usergroups_table.setCellWidget(row, 7, reserved)

        delete_button = QPushButton("✕")
        delete_button.setToolTip(tr("multiplayer.config.usergroups.remove"))
        delete_button.clicked.connect(lambda _=False, current_row=row: self._remove_usergroup_row_with_confirm(current_row))
        self._usergroups_table.setCellWidget(row, 8, delete_button)

        self._on_form_changed()

    def _remove_usergroup_row_with_confirm(self, row: int) -> None:
        current_row = row
        sender = self.sender()
        if isinstance(sender, QPushButton):
            for index in range(self._usergroups_table.rowCount()):
                if self._usergroups_table.cellWidget(index, 8) is sender:
                    current_row = index
                    break
        if current_row < 0 or current_row >= self._usergroups_table.rowCount():
            return

        group_item = self._usergroups_table.item(current_row, 0)
        group_name = group_item.text().strip() if group_item is not None else ""
        answer = QMessageBox.question(
            self,
            tr("multiplayer.config.usergroups.delete.title"),
            tr("multiplayer.config.usergroups.delete.text", name=group_name or "-")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._usergroups_table.removeRow(current_row)
        self._on_form_changed()

    def _add_ban_row(self, steam_id: str = "", player_name: str = "") -> None:
        row = self._bans_table.rowCount()
        self._bans_table.insertRow(row)
        self._bans_table.setItem(row, 0, QTableWidgetItem(steam_id))
        self._bans_table.setItem(row, 1, QTableWidgetItem(player_name))
        delete_button = QPushButton("✕")
        delete_button.setToolTip(tr("multiplayer.config.bans.remove"))
        delete_button.clicked.connect(lambda _=False, current_row=row: self._remove_ban_row_with_confirm(current_row))
        self._bans_table.setCellWidget(row, 2, delete_button)
        self._on_form_changed()

    def _remove_ban_row_with_confirm(self, row: int) -> None:
        current_row = row
        sender = self.sender()
        if isinstance(sender, QPushButton):
            for index in range(self._bans_table.rowCount()):
                if self._bans_table.cellWidget(index, 2) is sender:
                    current_row = index
                    break
        if current_row < 0 or current_row >= self._bans_table.rowCount():
            return
        answer = QMessageBox.question(
            self,
            tr("multiplayer.config.bans.delete.title"),
            tr("multiplayer.config.bans.delete.text")
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._bans_table.removeRow(current_row)
        self._on_form_changed()

    def _load_bans(self, payload: dict[str, object]) -> None:
        self._bans_table.setRowCount(0)
        bans = payload.get("bans")
        if bans is None:
            bans = payload.get("bannedAccounts", [])
        if not isinstance(bans, list):
            return
        for item in bans:
            if isinstance(item, str):
                self._add_ban_row(item, "")
            elif isinstance(item, dict):
                steam_id = str(item.get("id", "")).strip()
                name = str(item.get("name", "")).strip()
                if steam_id != "":
                    self._add_ban_row(steam_id, name)

    def _collect_bans(self) -> list[str]:
        result: list[str] = []
        for row in range(self._bans_table.rowCount()):
            steam_item = self._bans_table.item(row, 0)
            steam_id = steam_item.text().strip() if steam_item is not None else ""
            if steam_id != "":
                result.append(steam_id)
        return result

    def _collect_usergroups(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        for row in range(self._usergroups_table.rowCount()):
            name_item = self._usergroups_table.item(row, 0)
            password_item = self._usergroups_table.item(row, 1)
            name = name_item.text().strip() if name_item is not None else ""
            password = password_item.text() if password_item is not None else ""

            if name == "":
                continue

            def checked(col: int) -> bool:
                widget = self._usergroups_table.cellWidget(row, col)
                return isinstance(widget, QCheckBox) and widget.isChecked()

            reserved_widget = self._usergroups_table.cellWidget(row, 7)
            reserved = int(reserved_widget.value()) if isinstance(reserved_widget, QSpinBox) else 0

            result.append(
                {
                    "name": name,
                    "password": password,
                    "canKickBan": checked(2),
                    "canAccessInventories": checked(3),
                    "canEditWorld": checked(4),
                    "canEditBase": checked(5),
                    "canExtendBase": checked(6),
                    "reservedSlots": reserved,
                }
            )
        return result

    def _sync_json_from_form(self, show_errors: bool = True) -> bool:
        if self._sync_lock:
            return False
        payload = dict(self._payload)

        payload["name"] = self._name.text().strip() or "Enshrouded Server"
        payload["saveDirectory"] = self._save_directory.text().strip() or "./savegame"
        payload["logDirectory"] = self._log_directory.text().strip() or "./logs"
        payload["ip"] = self._ip.text().strip() or "0.0.0.0"
        payload["queryPort"] = int(self._query_port.value())
        payload["slotCount"] = int(self._slot_count.value())
        payload["voiceChatMode"] = self._voice_chat_mode.currentText()
        payload["enableVoiceChat"] = bool(self._enable_voice.isChecked())
        payload["enableTextChat"] = bool(self._enable_text.isChecked())
        payload["gameSettingsPreset"] = self._preset.currentText()
        payload["userGroups"] = self._collect_usergroups()

        payload["bans"] = self._collect_bans()
        if "bannedAccounts" in payload:
            payload.pop("bannedAccounts", None)

        tags = [entry.strip() for entry in self._tags.text().split(",") if entry.strip() != ""]
        payload["tags"] = tags

        game_settings = payload.get("gameSettings")
        if not isinstance(game_settings, dict):
            game_settings = {}
        game_settings = dict(game_settings)
        game_settings["playerHealthFactor"] = float(self._player_health.value())
        game_settings["playerManaFactor"] = float(self._player_mana.value())
        game_settings["playerStaminaFactor"] = float(self._player_stamina.value())
        game_settings["playerBodyHeatFactor"] = float(self._body_heat.value())
        game_settings["playerDivingTimeFactor"] = float(self._diving_time.value())
        game_settings["enableDurability"] = bool(self._enable_durability.isChecked())
        game_settings["enableStarvingDebuff"] = bool(self._enable_starving.isChecked())
        game_settings["foodBuffDurationFactor"] = float(self._food_buff_duration.value())
        game_settings["shroudTimeFactor"] = float(self._shroud_time.value())
        game_settings["enemyDamageFactor"] = float(self._enemy_damage.value())
        game_settings["enemyHealthFactor"] = float(self._enemy_health.value())
        game_settings["bossDamageFactor"] = float(self._boss_damage.value())
        game_settings["bossHealthFactor"] = float(self._boss_health.value())
        game_settings["miningDamageFactor"] = float(self._mining_damage.value())
        game_settings["resourceDropStackAmountFactor"] = float(self._resource_drop.value())
        game_settings["factoryProductionSpeedFactor"] = float(self._factory_speed.value())
        game_settings["perkUpgradeRecyclingFactor"] = float(self._recycling_factor.value())
        game_settings["perkCostFactor"] = float(self._perk_cost.value())
        game_settings["experienceCombatFactor"] = float(self._xp_combat.value())
        game_settings["experienceMiningFactor"] = float(self._xp_mining.value())
        game_settings["experienceExplorationQuestsFactor"] = float(self._xp_exploration.value())
        game_settings["enemyStaminaFactor"] = float(self._enemy_stamina.value())
        game_settings["enemyPerceptionRangeFactor"] = float(self._enemy_perception.value())
        game_settings["threatBonus"] = float(self._threat_bonus.value())
        game_settings["plantGrowthSpeedFactor"] = float(self._plant_growth.value())
        hunger_ns = int(self._from_hunger_seconds.value()) * 1_000_000_000
        day_ns = int(self._day_time_seconds.value()) * 1_000_000_000
        night_ns = int(self._night_time_seconds.value()) * 1_000_000_000
        game_settings["fromHungerToStarving"] = hunger_ns
        game_settings["dayTimeDuration"] = day_ns
        game_settings["nightTimeDuration"] = night_ns
        game_settings["weatherFrequency"] = self._weather_frequency.currentText()
        game_settings["fishingDifficulty"] = self._fishing_difficulty.currentText()
        game_settings["randomSpawnerAmount"] = self._random_spawner_amount.currentText()
        game_settings["aggroPoolAmount"] = self._aggro_pool_amount.currentText()
        game_settings["tombstoneMode"] = self._tombstone_mode.currentText()
        game_settings["curseModifier"] = self._curse_modifier.currentText()
        game_settings["tamingStartleRepercussion"] = self._taming_repercussion.currentText()
        game_settings["pacifyAllEnemies"] = bool(self._pacify_enemies.isChecked())
        game_settings["enableGliderTurbulences"] = bool(self._glider_turbulence.isChecked())
        payload["gameSettings"] = game_settings

        self._payload = payload
        self._sync_lock = True
        self._json_editor.setPlainText(json.dumps(payload, indent=2, ensure_ascii=False))
        self._sync_lock = False
        return True

    def _sync_form_from_json(self, show_errors: bool = True) -> bool:
        if self._sync_lock:
            return False
        try:
            payload = json.loads(self._json_editor.toPlainText())
        except json.JSONDecodeError as error:
            if show_errors:
                QMessageBox.warning(self, tr("common.error"), tr("multiplayer.config.invalid_json", error=str(error)))
            return False

        if not isinstance(payload, dict):
            if show_errors:
                QMessageBox.warning(self, tr("common.error"), tr("multiplayer.config.invalid_json_root"))
            return False

        validation_error = self._validate_payload(payload)
        if validation_error is not None:
            if show_errors:
                QMessageBox.warning(self, tr("common.error"), validation_error)
            return False

        self._payload = payload
        self._load_form_from_payload()
        return True

    def _wire_form_autosync(self) -> None:
        self._usergroups_table.itemChanged.connect(self._on_form_changed)
        self._bans_table.itemChanged.connect(self._on_form_changed)
        for line_edit in self.findChildren(QLineEdit):
            if line_edit is self._tags:
                line_edit.textEdited.connect(self._on_form_changed)
            else:
                line_edit.textChanged.connect(self._on_form_changed)
        for combo in self.findChildren(QComboBox):
            combo.currentIndexChanged.connect(self._on_form_changed)
        for check in self.findChildren(QCheckBox):
            check.stateChanged.connect(self._on_form_changed)
        for spin in self.findChildren(QSpinBox):
            spin.valueChanged.connect(self._on_form_changed)
        for dspin in self.findChildren(QDoubleSpinBox):
            dspin.valueChanged.connect(self._on_form_changed)
        

    def _on_form_changed(self, *_args) -> None:
        self._sync_json_from_form(show_errors=False)

    def _on_json_changed(self) -> None:
        self._sync_form_from_json(show_errors=False)

    def _insert_tag_completion(self, tag: str) -> None:
        text = self._tags.text()
        cursor_pos = self._tags.cursorPosition()

        start = text.rfind(",", 0, cursor_pos)
        start = 0 if start < 0 else start + 1
        end = text.find(",", cursor_pos)
        end = len(text) if end < 0 else end

        left = text[:start]
        right = text[end:]
        left_clean = left.rstrip()
        if left_clean and not left_clean.endswith(","):
            left_clean = f"{left_clean}, "
        elif left_clean == "":
            left_clean = ""

        new_text = f"{left_clean}{tag}"
        if right.strip() != "":
            new_text = f"{new_text}, {right.lstrip(' ,')}"
        else:
            new_text = f"{new_text}, "

        self._tags.setText(new_text)
        self._tags.setCursorPosition(len(left_clean + tag) + 2)

    def _save(self) -> None:
        if self._tabs.currentIndex() == 0:
            if not self._sync_json_from_form(show_errors=True):
                return
        else:
            if not self._sync_form_from_json(show_errors=True):
                return
        try:
            parsed = json.loads(self._json_editor.toPlainText())
        except json.JSONDecodeError as error:
            QMessageBox.warning(self, tr("common.error"), tr("multiplayer.config.invalid_json", error=str(error)))
            return

        if not isinstance(parsed, dict):
            QMessageBox.warning(self, tr("common.error"), tr("multiplayer.config.invalid_json_root"))
            return

        validation_error = self._validate_payload(parsed)
        if validation_error is not None:
            QMessageBox.warning(self, tr("common.error"), validation_error)
            return

        self._payload = parsed
        self.accept()

    def payload(self) -> dict[str, object]:
        return dict(self._payload)

    def _validate_payload(self, payload: dict[str, object]) -> str | None:
        name = payload.get("name")
        if not isinstance(name, str) or name.strip() == "":
            return tr("multiplayer.config.error.name_required")

        save_dir = payload.get("saveDirectory")
        if not isinstance(save_dir, str) or save_dir.strip() == "":
            return tr("multiplayer.config.error.save_dir_required")

        log_dir = payload.get("logDirectory")
        if not isinstance(log_dir, str) or log_dir.strip() == "":
            return tr("multiplayer.config.error.log_dir_required")

        query_port = payload.get("queryPort")
        if not isinstance(query_port, int) or not (1 <= query_port <= 65535):
            return tr("multiplayer.config.error.query_port_range")

        slot_count = payload.get("slotCount")
        if not isinstance(slot_count, int) or not (1 <= slot_count <= 16):
            return tr("multiplayer.config.error.slot_count_range")

        voice_mode = payload.get("voiceChatMode")
        if voice_mode not in {"Proximity", "Global"}:
            return tr("multiplayer.config.error.voice_mode")

        for bool_key in ("enableVoiceChat", "enableTextChat"):
            if not isinstance(payload.get(bool_key), bool):
                return tr("multiplayer.config.error.boolean", key=bool_key)

        user_groups = payload.get("userGroups")
        if not isinstance(user_groups, list):
            return tr("multiplayer.config.error.usergroups_list")
        for index, group in enumerate(user_groups, start=1):
            if not isinstance(group, dict):
                return tr("multiplayer.config.error.usergroup_item", index=index)
            if not isinstance(group.get("name"), str) or str(group.get("name")).strip() == "":
                return tr("multiplayer.config.error.usergroup_name", index=index)
            if not isinstance(group.get("password"), str):
                return tr("multiplayer.config.error.usergroup_password", index=index)
            reserved_slots = group.get("reservedSlots")
            if not isinstance(reserved_slots, int) or not (0 <= reserved_slots <= 16):
                return tr("multiplayer.config.error.usergroup_reserved", index=index)

        game_settings = payload.get("gameSettings")
        if not isinstance(game_settings, dict):
            return tr("multiplayer.config.error.gamesettings_object")

        constraints: dict[str, tuple[float, float]] = {
            "playerHealthFactor": (0.25, 4.0),
            "playerManaFactor": (0.25, 4.0),
            "playerStaminaFactor": (0.25, 4.0),
            "playerBodyHeatFactor": (0.5, 2.0),
            "playerDivingTimeFactor": (0.5, 2.0),
            "foodBuffDurationFactor": (0.5, 2.0),
            "shroudTimeFactor": (0.5, 2.0),
            "enemyDamageFactor": (0.25, 5.0),
            "enemyHealthFactor": (0.25, 4.0),
            "bossDamageFactor": (0.2, 5.0),
            "bossHealthFactor": (0.2, 5.0),
            "miningDamageFactor": (0.5, 2.0),
            "resourceDropStackAmountFactor": (0.25, 2.0),
        }
        for key, (min_value, max_value) in constraints.items():
            value = game_settings.get(key)
            if not isinstance(value, (int, float)):
                return tr("multiplayer.config.error.numeric", key=key)
            if float(value) < min_value or float(value) > max_value:
                return tr("multiplayer.config.error.range", key=key, min=min_value, max=max_value)

        for key in ("enableDurability", "enableStarvingDebuff"):
            value = game_settings.get(key)
            if not isinstance(value, bool):
                return tr("multiplayer.config.error.boolean", key=key)

        option_sets: dict[str, set[str]] = {
            "weatherFrequency": {"Disabled", "Rare", "Normal", "Often"},
            "fishingDifficulty": {"VeryEasy", "Easy", "Normal", "Hard", "VeryHard"},
            "randomSpawnerAmount": {"Few", "Normal", "Many", "Extreme"},
            "aggroPoolAmount": {"Few", "Normal", "Many", "Extreme"},
            "tombstoneMode": {"AddBackpackMaterials", "Everything", "NoTombstone"},
            "curseModifier": {"Easy", "Normal", "Hard"},
            "tamingStartleRepercussion": {"KeepProgress", "LoseSomeProgress", "LoseAllProgress"},
        }
        for key, valid_values in option_sets.items():
            value = game_settings.get(key)
            if not isinstance(value, str) or value not in valid_values:
                return tr("multiplayer.config.error.option", key=key)

        if not isinstance(game_settings.get("pacifyAllEnemies"), bool):
            return tr("multiplayer.config.error.boolean", key="pacifyAllEnemies")
        if not isinstance(game_settings.get("enableGliderTurbulences"), bool):
            return tr("multiplayer.config.error.boolean", key="enableGliderTurbulences")

        integer_constraints: dict[str, tuple[int, int]] = {
            "fromHungerToStarving": (300_000_000_000, 1_200_000_000_000),
            "dayTimeDuration": (120_000_000_000, 3_600_000_000_000),
            "nightTimeDuration": (120_000_000_000, 3_600_000_000_000),
        }
        for key, (min_value, max_value) in integer_constraints.items():
            value = game_settings.get(key)
            if not isinstance(value, int):
                return tr("multiplayer.config.error.numeric", key=key)
            if value < min_value or value > max_value:
                return tr("multiplayer.config.error.range", key=key, min=min_value, max=max_value)

        bans = payload.get("bans")
        if bans is not None and not isinstance(bans, list):
            return "bans muss ein Array sein."

        return None

    def _retranslate(self) -> None:
        self.setWindowTitle(tr("multiplayer.config.title", profile=self._profile_name))
        self._headline.setText(tr("multiplayer.config.title", profile=self._profile_name))
        self._path_label.setText(tr("multiplayer.config.path", path=self._remote_path))
        self._section_basic.setText(tr("multiplayer.config.section.basic"))
        self._section_chat.setText(tr("multiplayer.config.section.chat"))
        self._section_permissions.setText(tr("multiplayer.config.section.permissions"))
        self._section_gamesettings.setText(tr("multiplayer.config.section.gamesettings"))
        self._game_settings_hint.setText(tr("multiplayer.config.hint.custom_required"))
        self._section_bans.setText(tr("multiplayer.config.section.bans"))
        self._ban_info.setText(tr("multiplayer.config.bans.info"))
        self._footer_hint.setText(tr("multiplayer.config.footer.server_off_hint"))
