"""Round trip through a real RabbitMQ; runs only when RABBITMQ_URL is set."""

import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.environ.get("RABBITMQ_URL"), reason="RABBITMQ_URL not set"),
]


def test_round_trip() -> None:
    app.dependency_overrides.clear()
    text = f"integration-{uuid.uuid4()}"
    with TestClient(app) as client:  # runs the lifespan: real connection
        assert client.get("/health").json()["rabbitmq"] == "connected"
        assert client.post("/messages", json={"text": text}).status_code == 202
        for _ in range(50):
            if any(m["text"] == text for m in client.get("/messages").json()):
                return
            time.sleep(0.1)
    pytest.fail("message not consumed within 5 s")
