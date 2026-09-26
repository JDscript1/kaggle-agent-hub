from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock


class LogStore:
    def __init__(self, max_lines: int = 1000) -> None:
        self._lines: deque[str] = deque(maxlen=max_lines)
        self._lock = Lock()

    def add(self, message: str, level: str = "INFO") -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{stamp}] [{level}] {message}"
        with self._lock:
            self._lines.append(line)

    def text(self) -> str:
        with self._lock:
            return "\n".join(self._lines)

    def clear(self) -> None:
        with self._lock:
            self._lines.clear()


LOGS = LogStore()
