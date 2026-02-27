from __future__ import annotations

import logging

from core.profiles.models import Profile
from core.remote.client_base import RemoteClient
from core.remote.ftp_client import FTPClient
from core.remote.sftp_client import SFTPClient


def create_client(profile: Profile, password: str, logger: logging.Logger) -> RemoteClient:
    protocol = profile.protocol.lower()
    if protocol in {"ftp", "ftps"}:
        return FTPClient(profile=profile, password=password)
    if protocol == "sftp":
        return SFTPClient(profile=profile, password=password)

    logger.error("Unsupported profile protocol: %s", protocol)
    raise ValueError(f"Unsupported protocol: {protocol}")
