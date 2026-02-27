from __future__ import annotations

from dataclasses import replace
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.automations.models import AutomationJob, AutomationJobType
from i18n.i18n import get_i18n, tr
from storage.repositories import ProfileRepository


class AutomationJobDialog(QDialog):
    def __init__(
        self,
        connection: sqlite3.Connection,
        job: AutomationJob | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._source_job = job
        self._profile_repo = ProfileRepository(connection)

        self.setModal(True)
        self.setMinimumWidth(640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title_label = QLabel()
        self._title_label.setObjectName("panelTitle")
        layout.addWidget(self._title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self._name_edit = QLineEdit()
        form.addRow(self._label("name"), self._name_edit)

        self._enabled_checkbox = QCheckBox()
        form.addRow(self._label("enabled"), self._enabled_checkbox)

        self._type_combo = QComboBox()
        self._type_combo.currentIndexChanged.connect(self._update_type_fields_visibility)
        form.addRow(self._label("type"), self._type_combo)

        schedule_row = QGridLayout()
        self._hour_combo = QComboBox()
        for hour in range(0, 24):
            self._hour_combo.addItem(f"{hour:02d}", hour)

        self._minute_combo = QComboBox()
        for minute in range(0, 60):
            self._minute_combo.addItem(f"{minute:02d}", minute)

        schedule_row.addWidget(self._hour_combo, 0, 0)
        schedule_row.addWidget(QLabel(":"), 0, 1)
        schedule_row.addWidget(self._minute_combo, 0, 2)

        schedule_widget = QWidget()
        schedule_widget.setLayout(schedule_row)
        form.addRow(self._label("hour"), schedule_widget)

        weekdays_widget = QWidget()
        weekdays_layout = QHBoxLayout(weekdays_widget)
        weekdays_layout.setContentsMargins(0, 0, 0, 0)
        weekdays_layout.setSpacing(6)

        self._weekday_checks: dict[int, QCheckBox] = {}
        for weekday in range(0, 7):
            checkbox = QCheckBox()
            self._weekday_checks[weekday] = checkbox
            weekdays_layout.addWidget(checkbox)

        self._daily_button = QPushButton()
        self._daily_button.setObjectName("smallToolButton")
        self._daily_button.clicked.connect(self._select_all_weekdays)
        weekdays_layout.addWidget(self._daily_button)
        form.addRow(self._label("weekdays"), weekdays_widget)

        self._profile_combo = QComboBox()
        form.addRow(self._label("profile"), self._profile_combo)

        self._remote_path_edit = QLineEdit()
        form.addRow(self._label("remote_path"), self._remote_path_edit)

        source_row_widget = QWidget()
        source_row_layout = QHBoxLayout(source_row_widget)
        source_row_layout.setContentsMargins(0, 0, 0, 0)
        source_row_layout.setSpacing(8)
        self._source_dir_edit = QLineEdit()
        self._source_dir_browse = QPushButton()
        self._source_dir_browse.setObjectName("smallToolButton")
        self._source_dir_browse.clicked.connect(self._browse_source_dir)
        source_row_layout.addWidget(self._source_dir_edit, 1)
        source_row_layout.addWidget(self._source_dir_browse)
        form.addRow(self._label("source_dir"), source_row_widget)

        self._roll_mode_combo = QComboBox()
        self._roll_mode_combo.currentIndexChanged.connect(self._update_roll_fields_visibility)
        form.addRow(self._label("roll_mode"), self._roll_mode_combo)

        self._fixed_roll_combo = QComboBox()
        for roll in range(0, 10):
            self._fixed_roll_combo.addItem(str(roll), roll)
        form.addRow(self._label("roll_fixed"), self._fixed_roll_combo)

        self._keep_last_n = QSpinBox()
        self._keep_last_n.setRange(1, 999)
        form.addRow(self._label("keep_last_n"), self._keep_last_n)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self._cancel_button)
        self._save_button = QPushButton()
        self._save_button.setObjectName("primaryButton")
        self._save_button.clicked.connect(self._on_save)
        buttons.addWidget(self._save_button)
        layout.addLayout(buttons)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self._populate_static_items()
        self._populate_profiles()
        self._fill_from_job()
        self.retranslate_ui()

    def _label(self, field: str) -> QLabel:
        label = QLabel()
        label.setObjectName(f"automationJobDialogLabel_{field}")
        return label

    def _populate_static_items(self) -> None:
        self._type_combo.clear()
        self._type_combo.addItem("", AutomationJobType.SERVER_BACKUP.value)
        self._type_combo.addItem("", AutomationJobType.SCHEDULED_UPLOAD.value)

        self._roll_mode_combo.clear()
        self._roll_mode_combo.addItem("", "latest")
        self._roll_mode_combo.addItem("", "fixed")

    def _populate_profiles(self) -> None:
        selected_profile = self._profile_combo.currentData()
        self._profile_combo.clear()
        for profile in self._profile_repo.list_profiles():
            if profile.id is None:
                continue
            self._profile_combo.addItem(profile.name, profile.id)

        if selected_profile is not None:
            index = self._profile_combo.findData(selected_profile)
            if index >= 0:
                self._profile_combo.setCurrentIndex(index)

    def _fill_from_job(self) -> None:
        if self._source_job is None:
            self._enabled_checkbox.setChecked(True)
            self._name_edit.setText("")
            self._type_combo.setCurrentIndex(0)
            self._hour_combo.setCurrentIndex(0)
            self._minute_combo.setCurrentIndex(0)
            self._select_all_weekdays()
            self._remote_path_edit.setText("")
            self._source_dir_edit.setText("")
            self._roll_mode_combo.setCurrentIndex(0)
            self._fixed_roll_combo.setCurrentIndex(0)
            self._keep_last_n.setValue(10)
            self._update_type_fields_visibility()
            self._update_roll_fields_visibility()
            return

        job = self._source_job
        self._enabled_checkbox.setChecked(job.enabled)
        self._name_edit.setText(job.name)

        type_index = self._type_combo.findData(job.job_type.value)
        self._type_combo.setCurrentIndex(type_index if type_index >= 0 else 0)

        hour_index = self._hour_combo.findData(job.schedule_hour)
        minute_index = self._minute_combo.findData(job.schedule_minute)
        self._hour_combo.setCurrentIndex(hour_index if hour_index >= 0 else 0)
        self._minute_combo.setCurrentIndex(minute_index if minute_index >= 0 else 0)

        self._set_weekdays(job.schedule_weekdays)

        profile_index = self._profile_combo.findData(job.profile_id)
        self._profile_combo.setCurrentIndex(profile_index if profile_index >= 0 else 0)

        self._remote_path_edit.setText(job.remote_path or "")
        self._source_dir_edit.setText(job.source_local_dir or "")

        roll_mode_index = self._roll_mode_combo.findData(job.upload_roll_mode)
        self._roll_mode_combo.setCurrentIndex(roll_mode_index if roll_mode_index >= 0 else 0)

        fixed_roll_index = self._fixed_roll_combo.findData(job.upload_fixed_roll if job.upload_fixed_roll is not None else 0)
        self._fixed_roll_combo.setCurrentIndex(fixed_roll_index if fixed_roll_index >= 0 else 0)

        self._keep_last_n.setValue(max(1, int(job.keep_last_n)))

        self._update_type_fields_visibility()
        self._update_roll_fields_visibility()

    def _set_weekdays(self, schedule_weekdays: str) -> None:
        if schedule_weekdays.strip() == "*":
            self._select_all_weekdays()
            return

        selected: set[int] = set()
        for part in schedule_weekdays.split(","):
            cleaned = part.strip()
            if cleaned == "":
                continue
            try:
                day = int(cleaned)
            except ValueError:
                continue
            if 0 <= day <= 6:
                selected.add(day)

        for weekday, checkbox in self._weekday_checks.items():
            checkbox.setChecked(weekday in selected)

    def _select_all_weekdays(self) -> None:
        for checkbox in self._weekday_checks.values():
            checkbox.setChecked(True)

    def _browse_source_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            tr("automations.dialog.field.source_dir"),
            self._source_dir_edit.text().strip(),
        )
        if selected:
            self._source_dir_edit.setText(selected)

    def _update_type_fields_visibility(self) -> None:
        job_type = str(self._type_combo.currentData())
        is_upload = job_type == AutomationJobType.SCHEDULED_UPLOAD.value

        self._source_dir_edit.setVisible(is_upload)
        self._source_dir_browse.setVisible(is_upload)
        self._roll_mode_combo.setVisible(is_upload)
        self._fixed_roll_combo.setVisible(is_upload)

        source_label = self._find_label("source_dir")
        roll_mode_label = self._find_label("roll_mode")
        fixed_roll_label = self._find_label("roll_fixed")
        if source_label is not None:
            source_label.setVisible(is_upload)
        if roll_mode_label is not None:
            roll_mode_label.setVisible(is_upload)
        if fixed_roll_label is not None:
            fixed_roll_label.setVisible(is_upload)

        keep_visible = not is_upload
        self._keep_last_n.setVisible(keep_visible)
        keep_label = self._find_label("keep_last_n")
        if keep_label is not None:
            keep_label.setVisible(keep_visible)

    def _update_roll_fields_visibility(self) -> None:
        is_fixed = str(self._roll_mode_combo.currentData()) == "fixed"
        self._fixed_roll_combo.setVisible(is_fixed)
        label = self._find_label("roll_fixed")
        if label is not None:
            label.setVisible(is_fixed and self._fixed_roll_combo.isVisible())

    def _find_label(self, field: str) -> QLabel | None:
        return self.findChild(QLabel, f"automationJobDialogLabel_{field}")

    def _on_save(self) -> None:
        if self._validate():
            self.accept()

    def _validate(self) -> bool:
        if self._name_edit.text().strip() == "":
            QMessageBox.warning(self, tr("common.error"), tr("automations.dialog.error.name_required"))
            return False

        if self._profile_combo.currentData() is None:
            QMessageBox.warning(self, tr("common.error"), tr("automations.dialog.error.profile_required"))
            return False

        selected_weekdays = self._selected_weekdays()
        if len(selected_weekdays) == 0:
            QMessageBox.warning(self, tr("common.error"), tr("automations.dialog.error.weekdays_required"))
            return False

        is_upload = str(self._type_combo.currentData()) == AutomationJobType.SCHEDULED_UPLOAD.value
        if is_upload:
            source_dir = self._source_dir_edit.text().strip()
            if source_dir == "":
                QMessageBox.warning(self, tr("common.error"), tr("automations.dialog.error.source_required"))
                return False

        return True

    def to_job(self) -> AutomationJob:
        schedule_weekdays = self._serialize_weekdays(self._selected_weekdays())
        job = AutomationJob(
            id=self._source_job.id if self._source_job is not None else None,
            name=self._name_edit.text().strip(),
            enabled=self._enabled_checkbox.isChecked(),
            job_type=AutomationJobType(str(self._type_combo.currentData())),
            schedule_minute=int(self._minute_combo.currentData()),
            schedule_hour=int(self._hour_combo.currentData()),
            schedule_weekdays=schedule_weekdays,
            profile_id=int(self._profile_combo.currentData()) if self._profile_combo.currentData() is not None else None,
            remote_path=self._remote_path_edit.text().strip() or None,
            source_local_dir=self._source_dir_edit.text().strip() or None,
            upload_roll_mode=str(self._roll_mode_combo.currentData()),
            upload_fixed_roll=int(self._fixed_roll_combo.currentData()) if str(self._roll_mode_combo.currentData()) == "fixed" else None,
            keep_last_n=int(self._keep_last_n.value()),
            last_run_at=self._source_job.last_run_at if self._source_job is not None else None,
            last_status=self._source_job.last_status if self._source_job is not None else None,
            last_message=self._source_job.last_message if self._source_job is not None else None,
            created_at=self._source_job.created_at if self._source_job is not None else None,
            updated_at=self._source_job.updated_at if self._source_job is not None else None,
        )

        if job.job_type == AutomationJobType.SERVER_BACKUP:
            return replace(
                job,
                source_local_dir=None,
                upload_roll_mode="latest",
                upload_fixed_roll=None,
            )

        return job

    def _selected_weekdays(self) -> list[int]:
        selected: list[int] = []
        for weekday, checkbox in self._weekday_checks.items():
            if checkbox.isChecked():
                selected.append(weekday)
        return selected

    def _serialize_weekdays(self, selected: list[int]) -> str:
        ordered = sorted(set(selected))
        if ordered == [0, 1, 2, 3, 4, 5, 6]:
            return "*"
        return ",".join(str(day) for day in ordered)

    def retranslate_ui(self, _language: str | None = None) -> None:
        if self._source_job is None:
            self.setWindowTitle(tr("automations.dialog.title.add"))
            self._title_label.setText(tr("automations.dialog.title.add"))
        else:
            title = tr("automations.dialog.title.edit", name=self._source_job.name)
            self.setWindowTitle(title)
            self._title_label.setText(title)

        self._set_label_text("name", tr("automations.dialog.field.name"))
        self._set_label_text("enabled", tr("automations.dialog.field.enabled"))
        self._set_label_text("type", tr("automations.dialog.field.type"))
        self._set_label_text("hour", tr("automations.dialog.field.hour"))
        self._set_label_text("weekdays", tr("automations.dialog.field.weekdays"))
        self._set_label_text("profile", tr("automations.dialog.field.profile"))
        self._set_label_text("remote_path", tr("automations.dialog.field.remote_path"))
        self._set_label_text("source_dir", tr("automations.dialog.field.source_dir"))
        self._set_label_text("roll_mode", tr("automations.dialog.field.roll_mode"))
        self._set_label_text("roll_fixed", tr("automations.dialog.field.roll_fixed"))
        self._set_label_text("keep_last_n", tr("automations.dialog.field.keep_last_n"))

        self._enabled_checkbox.setText(tr("automations.enabled"))
        self._daily_button.setText(tr("automations.dialog.daily"))
        self._source_dir_browse.setText(tr("settings.browse"))
        self._save_button.setText(tr("common.save"))
        self._cancel_button.setText(tr("common.cancel"))

        self._type_combo.setItemText(0, tr("automations.type.server_backup"))
        self._type_combo.setItemText(1, tr("automations.type.scheduled_upload"))

        self._roll_mode_combo.setItemText(0, tr("automations.dialog.roll_mode.latest"))
        self._roll_mode_combo.setItemText(1, tr("automations.dialog.roll_mode.fixed"))

        weekday_keys = [
            "automations.weekday.mo",
            "automations.weekday.tu",
            "automations.weekday.we",
            "automations.weekday.th",
            "automations.weekday.fr",
            "automations.weekday.sa",
            "automations.weekday.su",
        ]
        for weekday, key in enumerate(weekday_keys):
            self._weekday_checks[weekday].setText(tr(key))

    def _set_label_text(self, field: str, text: str) -> None:
        label = self._find_label(field)
        if label is not None:
            label.setText(text)
