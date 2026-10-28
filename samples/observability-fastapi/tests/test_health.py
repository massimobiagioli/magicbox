import json
import logging
import sys

from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter
from app.main import app

# raise_server_exceptions=False: let the middleware turn errors into a 500.
client = TestClient(app, raise_server_exceptions=False)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_propagated() -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"


def test_request_log_has_fields(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app"):
        client.post("/orders", json={"item": "book", "quantity": 2})
    done = [r for r in caplog.records if r.getMessage() == "request completed"][-1]
    assert done.status == 201
    assert done.path == "/orders"
    assert done.duration_ms >= 0
    assert any(r.getMessage() == "order created" for r in caplog.records)


def test_unhandled_error_returns_500_with_request_id() -> None:
    response = client.get("/simulate/error", headers={"X-Request-ID": "err1"})
    assert response.status_code == 500
    assert response.json() == {"detail": "internal error", "request_id": "err1"}


def test_warning_returns_409() -> None:
    assert client.get("/simulate/warning").status_code == 409


def test_json_formatter_single_line_with_extras() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    record = logging.makeLogRecord(
        {
            "name": "t",
            "levelno": logging.ERROR,
            "levelname": "ERROR",
            "msg": "failed",
            "exc_info": exc_info,
            "order_id": "o1",
        }
    )
    line = JsonFormatter().format(record)
    assert "\n" not in line  # one Loki entry per log record
    entry = json.loads(line)
    assert entry["level"] == "ERROR"
    assert entry["order_id"] == "o1"
    assert "ValueError: boom" in entry["exception"]
