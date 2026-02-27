from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import uuid

from core.remote.client_base import RemoteClient


async def upload_local_file(client: RemoteClient, local_path: Path, remote_path_file: str) -> int:
    success, message, copied = await client.upload_file(Path(local_path), remote_path_file)
    if not success:
        raise RuntimeError(message)
    return copied


async def upload_index_latest(client: RemoteClient, remote_index_path: str, latest: int) -> int:
    payload = json.dumps({"latest": latest}, ensure_ascii=False, indent=2).encode("utf-8")
    success, message, copied = await client.upload_bytes(remote_index_path, payload)
    if not success:
        raise RuntimeError(message)
    return copied


async def download_remote_file_to_local_atomic(client: RemoteClient, remote_path_file: str, local_path: Path) -> int:
    target = Path(local_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    temp_path = target.with_name(f"{target.name}.tmp-{uuid.uuid4().hex}")

    try:
        success, message, copied = await client.download_file(remote_path_file, temp_path)
        if not success:
            raise RuntimeError(message)
        os.replace(temp_path, target)
        return copied
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def join_remote(root: str, file_name: str) -> str:
    return str(PurePosixPath(root) / file_name)
