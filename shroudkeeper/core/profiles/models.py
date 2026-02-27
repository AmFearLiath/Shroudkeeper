from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Profile:
    name: str
    protocol: str
    host: str
    port: int
    username: str
    remote_path: str
    passive_mode: bool = True
    verify_host_key: bool = True
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
