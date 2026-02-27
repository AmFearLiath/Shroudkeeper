from __future__ import annotations

import json
import logging
from pathlib import Path


class IndexFileService:
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("shroudkeeper.scanner.index")

    def read_latest(self, index_path: Path) -> int | None:
        if not index_path.exists():
            return None

        try:
            raw_content = index_path.read_bytes()
            decoded_content = raw_content.decode("utf-8")
            payload = json.loads(decoded_content)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._logger.warning("Invalid index JSON at %s", index_path.name)
            return None

        if not isinstance(payload, dict):
            return None

        latest = payload.get("latest")
        if isinstance(latest, int) and 0 <= latest <= 9:
            return latest

        return None

    def write_latest(self, index_path: Path, latest: int) -> None:
        if latest < 0 or latest > 9:
            raise ValueError("latest must be between 0 and 9")

        payload: dict[str, object] = {"latest": latest}

        if index_path.exists():
            try:
                raw_content = index_path.read_bytes()
                decoded_content = raw_content.decode("utf-8")
                loaded = json.loads(decoded_content)
                if isinstance(loaded, dict):
                    payload = loaded
                    payload["latest"] = latest
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                payload = {"latest": latest}

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
