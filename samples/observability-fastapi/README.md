# observability-fastapi

MagicBox sample (from `templates/python-fastapi-app`) for the `observability`
stack: the app writes **one JSON object per log line** on stdout; on MagicBox,
Alloy ships container logs to Loki and you explore them in Grafana.

```text
app (stdout JSON) -> Docker json-file log -> Alloy -> Loki -> Grafana (Explore)
```

No Loki client in the code: anything the container prints is collected, and
the Loki label `container` is the container name (`observability-fastapi`).

| Endpoint | Log produced |
|----------|--------------|
| `GET /health` | `request completed` at DEBUG (probes stay out of Loki by default) |
| `POST /orders` `{"item": "book", "quantity": 2}` | `order created` (INFO) + `request completed` |
| `GET /simulate/warning` | `stock not available` (WARNING), 409 |
| `GET /simulate/error` | `unhandled error` (ERROR) with traceback in the same line, 500 |

Every line has `ts`, `level`, `logger`, `msg`, `request_id` (from the
`X-Request-ID` header or generated, also returned in the response).

## Run on MagicBox

Logs reach Loki only when the container runs on MagicBox:

```bash
scp -4 -r samples/observability-fastapi massimo@magicbox.local:~/
ssh -4 massimo@magicbox.local 'cd observability-fastapi && sudo docker compose up --build -d'
# generate some traffic from the controller
for i in $(seq 20); do curl -s -X POST http://magicbox.local:8000/orders \
  -H 'content-type: application/json' -d '{"item":"book","quantity":2}' >/dev/null; done
curl -s http://magicbox.local:8000/simulate/warning; curl -s http://magicbox.local:8000/simulate/error
```

## Explore in Grafana

`https://magicbox.local/grafana/` (or `https://magicbox.local:3000/grafana/`) -> **Explore** -> data source **Loki**, paste a query:

| Goal | LogQL |
|------|-------|
| All app logs, fields parsed | `{container="observability-fastapi"} \| json` |
| Errors only | `{container="observability-fastapi"} \| json \| level="ERROR"` |
| One request end to end | `{container="observability-fastapi"} \| json \| request_id="<id>"` |
| Requests per status (5 min) | `sum by (status) (count_over_time({container="observability-fastapi"} \| json \| msg="request completed" [5m]))` |
| p95 latency (ms) | `quantile_over_time(0.95, {container="observability-fastapi"} \| json \| msg="request completed" \| unwrap duration_ms [5m])` |
| Orders per item | `sum by (item) (count_over_time({container="observability-fastapi"} \| json \| msg="order created" [1h]))` |

## Develop locally

```bash
uv sync
uv run uvicorn app.main:app --reload --no-access-log   # JSON logs in the terminal
uv run pytest && uv run ruff check .
```

Remove from MagicBox: `ssh -4 massimo@magicbox.local 'cd observability-fastapi && sudo docker compose down'`.
