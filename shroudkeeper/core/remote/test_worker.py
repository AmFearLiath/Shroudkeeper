from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QObject, Signal

from core.profiles.models import Profile
from core.remote.client_factory import create_client


class RemoteTestWorker(QObject):
    finished = Signal(bool, str)
    failed = Signal(str)

    def __init__(self, profile: Profile, password: str, logger: logging.Logger) -> None:
        super().__init__()
        self._profile = profile
        self._password = password
        self._logger = logger

    def run(self) -> None:
        try:
            success, message = asyncio.run(self._run_test())
            self.finished.emit(success, message)
        except Exception as error:
            self.failed.emit(str(error))

    async def _run_test(self) -> tuple[bool, str]:
        client = create_client(profile=self._profile, password=self._password, logger=self._logger)

        success, message = await client.test_connection()
        if not success:
            return False, message

        ensure_success, ensure_message = await client.ensure_dir(self._profile.remote_path)
        if not ensure_success:
            return False, ensure_message

        list_success, list_message, _entries = await client.list_dir(self._profile.remote_path)
        if not list_success:
            return False, list_message

        return True, message
