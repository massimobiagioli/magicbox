# Samples

Example applications that use the MagicBox default stacks. Each subfolder is
built from [`templates/python-fastapi-app`](../templates/python-fastapi-app/README.md)
and is self-contained (own `pyproject.toml`, `uv.lock`, Dockerfile). Comments
in the code mark the important choices (why, not what).

| Sample | Stack | What it shows |
|--------|-------|---------------|
| [rabbitmq-fastapi](rabbitmq-fastapi/README.md) | `rabbitmq` | Publish to and consume from a durable queue (aio-pika) |
| [observability-fastapi](observability-fastapi/README.md) | `observability` | JSON logs with request ids -> Alloy -> Loki; LogQL queries in Grafana |

Credentials come from environment variables (`.env`, git-ignored), set to the
values in the MagicBox vault. Run the samples from a computer on the MagicBox LAN.
