"""Unit tests with an in-memory broker; no RabbitMQ needed."""

from collections import deque

from fastapi.testclient import TestClient

from app.main import app, get_broker


class FakeBroker:
    queue_name = "test"

    def __init__(self, connected: bool = True) -> None:
        self.connected = connected
        self.received: deque[dict[str, str]] = deque()

    async def publish(self, text: str) -> None:
        self.received.append({"text": text, "received_at": "now"})


def client_with(broker: FakeBroker) -> TestClient:
    app.dependency_overrides[get_broker] = lambda: broker
    return TestClient(app)  # no context manager: lifespan (real RabbitMQ) is skipped


def test_health_connected() -> None:
    response = client_with(FakeBroker()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "rabbitmq": "connected"}


def test_health_disconnected() -> None:
    response = client_with(FakeBroker(connected=False)).get("/health")
    assert response.status_code == 503


def test_publish_and_list() -> None:
    client = client_with(FakeBroker())
    assert client.post("/messages", json={"text": "hello"}).status_code == 202
    assert client.get("/messages").json()[0]["text"] == "hello"


def test_publish_rejects_empty_text() -> None:
    assert client_with(FakeBroker()).post("/messages", json={"text": ""}).status_code == 422
