from __future__ import annotations

import os
import subprocess

from i18n.i18n import tr


try:
    import psutil
except Exception:  # pragma: no cover - optional dependency import fallback
    psutil = None


def is_process_running(process_name: str) -> bool:
    normalized = process_name.strip().lower()
    if normalized == "":
        return False

    if psutil is not None:
        try:
            for process in psutil.process_iter(["name"]):
                name = process.info.get("name")
                if isinstance(name, str) and name.lower() == normalized:
                    return True
            return False
        except Exception:
            pass

    if os.name == "nt":
        return _tasklist_check(normalized)

    return False


def _tasklist_check(process_name: str) -> bool:
    try:
        completed = subprocess.run(
            [
                "tasklist",
                "/FI",
                f"IMAGENAME eq {process_name}",
                "/FO",
                "CSV",
                "/NH",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return False

    output = (completed.stdout or "").strip()
    if output == "" or output.upper().startswith("INFO:"):
        return False

    return process_name in output.lower()


def can_write_singleplayer_files() -> bool:
    return not is_process_running("enshrouded.exe")


def singleplayer_write_block_message() -> str:
    return tr("transfers.error.game_running.text")
