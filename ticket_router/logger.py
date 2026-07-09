import json
import sys
from datetime import UTC, datetime
from typing import Any


def _emit(level: str, message: str, meta: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "message": message,
    }
    if meta:
        entry["meta"] = meta
    stream = sys.stderr if level == "error" else sys.stdout
    print(json.dumps(entry, default=str), file=stream)


class Logger:
    """Thin structured-JSON wrapper around plain stdout/stderr logging."""

    def info(self, message: str, meta: dict[str, Any] | None = None) -> None:
        _emit("info", message, meta)

    def warning(self, message: str, meta: dict[str, Any] | None = None) -> None:
        _emit("warning", message, meta)

    def error(self, message: str, meta: dict[str, Any] | None = None) -> None:
        _emit("error", message, meta)


logger = Logger()
