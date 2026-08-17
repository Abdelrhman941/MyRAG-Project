from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import click
from uvicorn.logging import DefaultFormatter

from .context import get_request_id

_STANDARD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "color_message",
}

_STATUS_COLORS = {2: "green", 3: "yellow", 4: "red", 5: "bright_red"}


def _format_value(key: str, value: object) -> str:
    if key == "status_code" and isinstance(value, int):
        color = _STATUS_COLORS.get(value // 100, "white")
        return click.style(str(value), fg=color, bold=True)
    return str(value)


def _extra_fields(record: logging.LogRecord) -> str:
    parts = [
        f"{click.style(key, dim=True)}={_format_value(key, value)}"
        for key, value in record.__dict__.items()
        if key not in _STANDARD_FIELDS and not key.startswith("_")
    ]
    if record.levelno >= logging.WARNING and (rid := get_request_id()):
        parts.append(f"{click.style('request_id', dim=True)}={rid}")
    return " ".join(parts)


class ConsoleFormatter(DefaultFormatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        base = super().formatMessage(record)
        extra = _extra_fields(record)
        if not extra:
            return base
        return f"{base} {click.style('|', dim=True)} {extra}"


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if rid := get_request_id():
            payload["request_id"] = rid

        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)[:2000]

        return json.dumps(payload, default=str, ensure_ascii=False)
