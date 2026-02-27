from __future__ import annotations

import logging
import sqlite3

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.automations.models import AutomationJob, AutomationJobType
from core.automations.runner import AutomationRunner
from core.automations.scheduler import AutomationScheduler
from i18n.i18n import get_i18n, tr
from storage.repositories import AutomationJobRepository, ProfileRepository
from ui.components.ev_page_header import EVPageHeader
from ui.widgets.automation_job_dialog import AutomationJobDialog


class AutomationsView(QWidget):
    def __init__(
        self,
        connection: sqlite3.Connection,
        scheduler: AutomationScheduler,
        runner: AutomationRunner,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self._connection = connection
        self._logger = logger
        self._scheduler = scheduler
        self._runner = runner
        self._job_repo = AutomationJobRepository(connection)
        self._profile_repo = ProfileRepository(connection)
        self._jobs_by_id: dict[int, AutomationJob] = {}
        self._profiles_by_id: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._header = EVPageHeader()

        self._refresh_button = QPushButton()
        self._refresh_button.setProperty("variant", "secondary")
        self._refresh_button.clicked.connect(self._reload_data)
        self._header.add_action(self._refresh_button)

        self._add_button = QPushButton()
        self._add_button.setProperty("variant", "primary")
        self._add_button.clicked.connect(self._on_add_job)
        self._header.add_action(self._add_button)

        layout.addWidget(self._header)

        panel = QFrame()
        panel.setObjectName("EVCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        scheduler_row = QHBoxLayout()
        scheduler_row.setSpacing(8)

        self._scheduler_label = QLabel()
        self._scheduler_label.setObjectName("infoBar")
        scheduler_row.addWidget(self._scheduler_label, 1)

        self._scheduler_toggle_button = QPushButton()
        self._scheduler_toggle_button.setProperty("variant", "secondary")
        self._scheduler_toggle_button.clicked.connect(self._toggle_scheduler)
        scheduler_row.addWidget(self._scheduler_toggle_button)

        panel_layout.addLayout(scheduler_row)

        self._jobs_table = QTableWidget(0, 8)
        self._jobs_table.setObjectName("EVTable")
        self._jobs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._jobs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._jobs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._jobs_table.setAlternatingRowColors(True)
        self._jobs_table.verticalHeader().setVisible(False)
        self._jobs_table.horizontalHeader().setStretchLastSection(False)
        self._jobs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._jobs_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._jobs_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        panel_layout.addWidget(self._jobs_table)

        self._status_label = QLabel()
        self._status_label.setObjectName("infoBar")
        panel_layout.addWidget(self._status_label)

        panel_layout.addStretch(1)

        layout.addWidget(panel)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self._scheduler.state_changed.connect(self._on_scheduler_state_changed)
        self._runner.job_finished.connect(self._on_job_finished)

        self._reload_data()
        self.retranslate_ui()

    def refresh_profiles(self) -> None:
        self._reload_data()

    def _reload_data(self) -> None:
        profiles = self._profile_repo.list_profiles()
        self._profiles_by_id = {
            profile.id: profile.name for profile in profiles if profile.id is not None
        }

        jobs = self._job_repo.list_jobs()
        self._jobs_by_id = {job.id: job for job in jobs if job.id is not None}
        self._render_jobs_table(jobs)

    def _render_jobs_table(self, jobs: list[AutomationJob]) -> None:
        self._jobs_table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            if job.id is None:
                continue

            enabled_checkbox = QCheckBox()
            enabled_checkbox.setChecked(job.enabled)
            enabled_checkbox.stateChanged.connect(
                lambda state, job_id=job.id: self._on_enabled_changed(job_id, state)
            )
            enabled_container = QWidget()
            enabled_layout = QHBoxLayout(enabled_container)
            enabled_layout.setContentsMargins(6, 0, 6, 0)
            enabled_layout.addWidget(enabled_checkbox)
            enabled_layout.addStretch(1)
            self._jobs_table.setCellWidget(row, 0, enabled_container)

            self._jobs_table.setItem(row, 1, QTableWidgetItem(job.name))
            self._jobs_table.setItem(row, 2, QTableWidgetItem(self._type_label(job.job_type)))
            self._jobs_table.setItem(row, 3, QTableWidgetItem(self._schedule_label(job)))
            profile_name = (
                self._profiles_by_id.get(job.profile_id)
                if job.profile_id is not None
                else None
            )
            self._jobs_table.setItem(row, 4, QTableWidgetItem(profile_name or tr("common.not_available")))
            self._jobs_table.setItem(row, 5, QTableWidgetItem(job.last_run_at or tr("common.not_available")))
            self._jobs_table.setItem(row, 6, QTableWidgetItem(self._status_label_for_table(job.last_status)))

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(6)

            edit_button = QPushButton(tr("automations.edit"))
            edit_button.setProperty("variant", "secondary")
            edit_button.clicked.connect(lambda _checked=False, job_id=job.id: self._on_edit_job(job_id))
            actions_layout.addWidget(edit_button)

            delete_button = QPushButton(tr("automations.delete"))
            delete_button.setProperty("variant", "danger")
            delete_button.clicked.connect(lambda _checked=False, job_id=job.id: self._on_delete_job(job_id))
            actions_layout.addWidget(delete_button)

            run_now_button = QPushButton(tr("automations.run_now"))
            run_now_button.setProperty("variant", "ghost")
            run_now_button.clicked.connect(lambda _checked=False, job_id=job.id: self._runner.run_job_now(job_id))
            actions_layout.addWidget(run_now_button)

            self._jobs_table.setCellWidget(row, 7, actions_widget)

        self._jobs_table.resizeRowsToContents()

    def _on_enabled_changed(self, job_id: int, state: int) -> None:
        job = self._job_repo.get_job(job_id)
        if job is None:
            return
        job.enabled = bool(state == Qt.CheckState.Checked.value)
        self._job_repo.update_job(job)
        self._reload_data()

    def _on_add_job(self) -> None:
        dialog = AutomationJobDialog(connection=self._connection, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        job = dialog.to_job()
        self._job_repo.create_job(job)
        self._reload_data()

    def _on_edit_job(self, job_id: int) -> None:
        job = self._job_repo.get_job(job_id)
        if job is None:
            return

        dialog = AutomationJobDialog(connection=self._connection, job=job, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated = dialog.to_job()
        self._job_repo.update_job(updated)
        self._reload_data()

    def _on_delete_job(self, job_id: int) -> None:
        job = self._job_repo.get_job(job_id)
        if job is None:
            return

        confirmed = QMessageBox.question(
            self,
            tr("automations.confirm.delete.title"),
            tr("automations.confirm.delete.text", name=job.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self._job_repo.delete_job(job_id)
        self._reload_data()

    def _toggle_scheduler(self) -> None:
        if self._scheduler.is_running():
            self._scheduler.stop()
        else:
            self._scheduler.start()
        self._update_scheduler_status()

    def _on_scheduler_state_changed(self, _is_running: bool) -> None:
        self._update_scheduler_status()

    def _on_job_finished(self, _job_id: int, status: str, message: str) -> None:
        status_text = self._status_label_for_table(status)
        self._status_label.setText(f"{status_text}: {message}")
        self._reload_data()

    def _update_scheduler_status(self) -> None:
        if self._scheduler.is_running():
            self._scheduler_label.setText(tr("automations.scheduler.running"))
            self._scheduler_toggle_button.setText(tr("automations.scheduler.stop"))
        else:
            self._scheduler_label.setText(tr("automations.scheduler.stopped"))
            self._scheduler_toggle_button.setText(tr("automations.scheduler.start"))

    def _status_label_for_table(self, status: str | None) -> str:
        if status == "success":
            return tr("automations.status.success")
        if status == "failed":
            return tr("automations.status.failed")
        if status == "skipped":
            return tr("automations.status.skipped")
        return tr("common.not_available")

    def _type_label(self, job_type: AutomationJobType) -> str:
        if job_type == AutomationJobType.SERVER_BACKUP:
            return tr("automations.type.server_backup")
        return tr("automations.type.scheduled_upload")

    def _schedule_label(self, job: AutomationJob) -> str:
        time_part = f"{job.schedule_hour:02d}:{job.schedule_minute:02d}"
        if job.schedule_weekdays.strip() == "*":
            return tr("automations.schedule.daily", time=time_part)

        weekdays = []
        key_map = {
            0: "automations.weekday.mo",
            1: "automations.weekday.tu",
            2: "automations.weekday.we",
            3: "automations.weekday.th",
            4: "automations.weekday.fr",
            5: "automations.weekday.sa",
            6: "automations.weekday.su",
        }
        for part in job.schedule_weekdays.split(","):
            cleaned = part.strip()
            if cleaned == "":
                continue
            try:
                value = int(cleaned)
            except ValueError:
                continue
            if value in key_map:
                weekdays.append(tr(key_map[value]))

        if weekdays == [tr("automations.weekday.mo"), tr("automations.weekday.tu"), tr("automations.weekday.we"), tr("automations.weekday.th"), tr("automations.weekday.fr")]:
            return tr("automations.schedule.weekdays", time=time_part)

        return tr("automations.schedule.custom", time=time_part, days=", ".join(weekdays))

    def retranslate_ui(self, _language: str | None = None) -> None:
        self._header.set_title(tr("automations.title"))
        self._add_button.setText(tr("automations.add"))
        self._refresh_button.setText(tr("automations.refresh"))

        self._jobs_table.setHorizontalHeaderLabels(
            [
                tr("automations.enabled"),
                tr("automations.table.name"),
                tr("automations.table.type"),
                tr("automations.table.schedule"),
                tr("automations.table.profile"),
                tr("automations.table.last_run"),
                tr("automations.table.last_status"),
                tr("automations.table.actions"),
            ]
        )

        self._update_scheduler_status()
        if self._status_label.text().strip() == "":
            self._status_label.setText(tr("automations.description"))

        self._reload_data()
