"""FastAPI sample: structured logs for Grafana + Loki + Alloy (observability stack)."""

import asyncio
import logging
import random
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.logging_config import configure_logging, request_id_var

# Configure logging at import time, before uvicorn handles the first request.
configure_logging()
log = logging.getLogger("app")

app = FastAPI(title="observability-fastapi", version="0.1.0")


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    # Correlation id: reuse the caller's X-Request-ID (e.g. from a proxy or
    # another service) or create one. Every log line of this request carries
    # it, so Grafana can show the whole story with {request_id="..."}.
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Unhandled error: log the traceback once, as JSON, with the request id,
        # and return a clean 500 that tells the caller which id to report.
        log.exception("unhandled error", extra={"path": request.url.path})
        response = JSONResponse(
            {"detail": "internal error", "request_id": request_id},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    # One "access log" line per request with numeric fields: Grafana can count
    # by status and compute latency percentiles with `| unwrap duration_ms`.
    # Docker's HEALTHCHECK calls /health every 30 s: log it at DEBUG so probes
    # do not flood Loki (set LOG_LEVEL=DEBUG to see them).
    level = logging.DEBUG if request.url.path == "/health" else logging.INFO
    log.log(
        level,
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    request_id_var.reset(token)
    return response


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe used by Docker HEALTHCHECK."""
    return {"status": "ok"}


class OrderIn(BaseModel):
    item: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=1000)


@app.post("/orders", status_code=status.HTTP_201_CREATED, tags=["demo"])
async def create_order(order: OrderIn) -> dict[str, str | int]:
    """Simulated business operation with variable latency."""
    order_id = uuid.uuid4().hex[:12]
    await asyncio.sleep(random.uniform(0.01, 0.3))  # stand-in for real work
    # Business event: log *what happened* with searchable fields, not a free
    # text sentence. Query: {container="observability-fastapi"} | json | msg="order created"
    log.info(
        "order created",
        extra={"order_id": order_id, "item": order.item, "quantity": order.quantity},
    )
    return {"order_id": order_id, "item": order.item, "quantity": order.quantity}


@app.get("/simulate/error", tags=["demo"])
def simulate_error() -> None:
    """Raise an unhandled exception to see a traceback in Loki."""
    raise RuntimeError("simulated failure")


@app.get("/simulate/warning", tags=["demo"])
def simulate_warning() -> None:
    """Handled client error: logged as WARNING, answered with 409."""
    # Expected failures are WARNING (not ERROR): alert on ERROR only, so
    # client mistakes do not page anyone.
    log.warning("stock not available", extra={"item": "demo"})
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="stock not available")
