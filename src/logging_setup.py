"""Shared logging configuration for the application."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_FILE = Path("data/logs/info-aggregator.log")

_STANDARD_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


def make_run_id(now: datetime | None = None) -> str:
    """Build a unique run identifier."""

    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y%m%d_%H%M%S_%f")


def resolve_run_log_path(log_file: str | Path, run_id: str) -> Path:
    """Resolve the final log file path for a run."""

    configured = Path(log_file)
    if configured == DEFAULT_LOG_FILE:
        return configured.with_name(f"{configured.stem}_{run_id}{configured.suffix}")
    return configured


def _record_extras(record: logging.LogRecord) -> dict[str, object]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _STANDARD_RECORD_FIELDS and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extras = _record_extras(record)
        if extras:
            payload["context"] = extras

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


class PrettyConsoleFormatter(logging.Formatter):
    """Format log records for human-readable console output."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).astimezone().strftime("%Y-%m-%d %H:%M:%S")
        extras = _record_extras(record)
        if extras:
            context = " ".join(f"{key}={value!r}" for key, value in sorted(extras.items()))
            return f"{timestamp} | {record.levelname:<7} | {record.getMessage()} | {context}"
        return f"{timestamp} | {record.levelname:<7} | {record.getMessage()}"


def setup_logging(level: str = "INFO", log_file: str | Path = DEFAULT_LOG_FILE) -> Path:
    """Configure root logging for console and file output."""

    log_level = getattr(logging, level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"invalid log level: {level}")

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(PrettyConsoleFormatter())

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "logging_configured",
        extra={"log_level": level.upper(), "log_file": str(log_path)},
    )
    return log_path
