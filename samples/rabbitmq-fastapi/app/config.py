"""Settings read from the environment (never hard-code credentials)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    rabbitmq_url: str
    queue: str


def load_settings() -> Settings:
    url = os.environ.get("RABBITMQ_URL")
    if not url:
        raise RuntimeError(
            "RABBITMQ_URL is not set, e.g. amqp://magicbox:<password>@magicbox.local:5672/"
        )
    return Settings(rabbitmq_url=url, queue=os.environ.get("RABBITMQ_QUEUE", "magicbox.samples"))
