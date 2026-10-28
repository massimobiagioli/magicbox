# rabbitmq-fastapi

MagicBox sample (from `templates/python-fastapi-app`): a FastAPI app that
publishes messages to the `rabbitmq` stack and consumes them from a durable
queue with aio-pika.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | 200 when connected to RabbitMQ, 503 otherwise |
| `POST /messages` `{"text": "..."}` | Publish a persistent message |
| `GET /messages` | Last 100 messages consumed by this instance |

```bash
cp .env.example .env                      # set the password (vault_rabbitmq_password)
uv sync
set -a; . ./.env; set +a
uv run uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
curl -X POST localhost:8000/messages -H 'content-type: application/json' -d '{"text":"hello"}'
curl localhost:8000/messages
uv run pytest                             # unit tests; + round trip when RABBITMQ_URL is set
docker compose up --build -d              # reads RABBITMQ_URL from .env
```

The queue is visible in the RabbitMQ UI: `http://magicbox.local:15672/` → Queues.
Requires the controller on the MagicBox LAN (firewall).
