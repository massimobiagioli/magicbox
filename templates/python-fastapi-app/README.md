# python-fastapi-app

FastAPI template: Python 3.15, uv-managed `.venv`, `GET /health`, Docker image,
Jenkins CI/CD for MagicBox. New app: `uv run tools/new_app.py <name>` in the
magicbox repository (manual: `manuals/how-to-create-new-app.pdf`).

```bash
uv sync                                        # create .venv from uv.lock
uv run uvicorn app.main:app --reload           # http://127.0.0.1:8000/health, docs at /docs
uv run pytest && uv run ruff check .           # tests + lint
docker compose up --build -d                   # container on port 8000 (HEALTHCHECK on /health)
```

## CI/CD on MagicBox

The Jenkins job is created by `make apps`; its name is the app name. A push
is picked up within 5 minutes.

| Branch | Stages |
|--------|--------|
| any | Prepare (`ci` image), Lint (ruff), Test (pytest) |
| `main` | + Build (`magicbox/<app>:<commit>`), Deploy (Portainer stack `<app>`), Verify (healthy) |

`deploy/stack.yml` publishes `127.0.0.1:${APP_PORT}` (port from the MagicBox
apps registry) to container port 8000; Kong serves it at
`https://magicbox.local/<app>`, with the `/<app>` prefix stripped. Nothing in
`Jenkinsfile` or `deploy/` is app-specific; if the app listens on another
port, change 8000 in `Dockerfile` and `deploy/stack.yml`.
