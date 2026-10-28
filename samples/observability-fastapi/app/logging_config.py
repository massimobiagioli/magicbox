"""JSON logging on stdout: one JSON object per line.

Why JSON: on MagicBox, Docker stores stdout in json-file logs, Alloy ships every
line to Loki, and Grafana's `| json` parser turns each key into a field you can
filter and aggregate on (level, status, duration_ms, request_id, ...). No
logging library or Loki client is needed in the app.
"""

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Request id of the request being handled. A ContextVar is per asyncio task, so
# concurrent requests never see each other's id.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

# Attributes every LogRecord has; anything else was passed via `extra=` and is
# emitted as a top-level JSON field.
# color_message is uvicorn's ANSI-coloured copy of msg: noise in Loki.
_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        # Business context passed as logger.info("...", extra={...}).
        entry |= {k: v for k, v in record.__dict__.items() if k not in _STANDARD_ATTRS}
        if record.exc_info:
            # Keep the traceback inside the same JSON line: Loki stores one entry
            # per line, so a multi-line traceback would be split and lost.
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)  # stdout: what Docker collects
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    # Route uvicorn's own loggers through the same JSON handler instead of its
    # plain-text format, so every line in Loki has the same shape.
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    # The middleware in app/main.py writes a richer access line (request id,
    # duration): silence uvicorn's plain one to avoid two lines per request.
    logging.getLogger("uvicorn.access").disabled = True
