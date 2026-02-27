from __future__ import annotations

import asyncio
import logging

from PySide6.QtCore import QObject, Signal

from core.profiles.models import Profile
from core.remote.client_factory import create_client
from core.server.server_world_service import ServerWorldService


class ServerScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, profile: Profile, password: str, logger: logging.Logger) -> None:
        super().__init__()
        self._profile = profile
        self._password = password
        self._logger = logger
        self._service = ServerWorldService(logger=logger)

    def run(self) -> None:
        try:
            result = asyncio.run(self._run_scan())
            self.finished.emit(result)
        except Exception as error:
            self.failed.emit(str(error))

    async def _run_scan(self):
        client = create_client(profile=self._profile, password=self._password, logger=self._logger)

        success, message = await client.test_connection()
        if not success:
            raise RuntimeError(message)

        return await self._service.scan_server_world(client=client, remote_root=self._profile.remote_path)
