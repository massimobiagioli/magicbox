# python-fastapi-app

FastAPI template: Python 3.15, uv-managed `.venv`, `GET /health`, Docker image.

```bash
uv sync                                        # create .venv from uv.lock
uv run uvicorn app.main:app --reload           # http://127.0.0.1:8000/health, docs at /docs
uv run pytest && uv run ruff check .           # tests + lint
docker compose up --build -d                   # container on port 8000 (HEALTHCHECK on /health)
```

New project: copy this folder, rename `name` in `pyproject.toml`, run `uv lock`.
