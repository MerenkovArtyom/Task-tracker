from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback


DEBUG_LOG_PATH = Path("/tmp/todo_tracker_menubar.log")


def debug_log(message: str) -> None:
    timestamp = datetime.now().isoformat(timespec="seconds")
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def debug_log_exception(prefix: str) -> None:
    debug_log(f"{prefix}\n{traceback.format_exc()}")
