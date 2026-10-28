"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(title="python-fastapi-app", version="0.1.0")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Liveness probe used by Docker HEALTHCHECK and load balancers."""
    return {"status": "ok"}
