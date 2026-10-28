"""FastAPI sample: publish messages to RabbitMQ and read what the consumer received."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from pydantic import BaseModel, Field

from app.broker import Broker
from app.config import load_settings


# Lifespan: open ONE connection per process at startup and close it on shutdown.
# Opening a connection per request would be slow and exhaust broker resources.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    app.state.broker = Broker(settings.rabbitmq_url, settings.queue)
    await app.state.broker.start()
    yield
    await app.state.broker.stop()


app = FastAPI(title="rabbitmq-fastapi", version="0.1.0", lifespan=lifespan)


# Validate input at the edge: an empty or huge body never reaches the broker.
class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


# Endpoints receive the broker through a dependency, so tests can swap it for
# an in-memory fake (app.dependency_overrides) without a running RabbitMQ.
def get_broker(request: Request) -> Broker:
    return request.app.state.broker


BrokerDep = Annotated[Broker, Depends(get_broker)]


@app.get("/health", tags=["health"])
def health(response: Response, broker: BrokerDep) -> dict[str, str]:
    """Liveness probe; 503 while the RabbitMQ connection is down."""
    # Report 503 when the broker is unreachable: Docker's HEALTHCHECK and load
    # balancers then see the instance as unhealthy instead of failing requests.
    if not broker.connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "rabbitmq": "disconnected"}
    return {"status": "ok", "rabbitmq": "connected"}


# 202 Accepted: the message is queued, not yet processed (asynchronous work).
@app.post("/messages", status_code=status.HTTP_202_ACCEPTED, tags=["messages"])
async def publish(message: MessageIn, broker: BrokerDep) -> dict[str, str]:
    """Publish a persistent message to the queue."""
    await broker.publish(message.text)
    return {"queued": broker.queue_name}


@app.get("/messages", tags=["messages"])
def received(broker: BrokerDep) -> list[dict[str, str]]:
    """Messages consumed from the queue by this instance (last 100)."""
    return list(broker.received)
