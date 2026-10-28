"""RabbitMQ publisher and consumer built on aio-pika."""

from collections import deque
from datetime import UTC, datetime

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection


class Broker:
    """Publishes to one durable queue and keeps the last received messages."""

    def __init__(self, url: str, queue: str, keep: int = 100) -> None:
        self.url = url
        self.queue_name = queue
        # Demo storage only: in-memory and per instance. A real consumer would
        # write to a database (see the PostgreSQL stack) and be idempotent.
        self.received: deque[dict[str, str]] = deque(maxlen=keep)
        self._connection: AbstractRobustConnection | None = None

    @property
    def connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed

    async def start(self) -> None:
        # connect_robust reconnects automatically after broker restarts.
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        # Prefetch: at most 10 unacknowledged messages in flight for this
        # consumer, so a slow instance does not hoard the queue.
        await self._channel.set_qos(prefetch_count=10)
        # durable=True: the queue definition survives a RabbitMQ restart.
        # Declaring is idempotent, so every instance can safely do it at startup.
        queue = await self._channel.declare_queue(self.queue_name, durable=True)
        await queue.consume(self._on_message)

    async def stop(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def publish(self, text: str) -> None:
        message = aio_pika.Message(
            body=text.encode(),
            content_type="text/plain",
            # PERSISTENT: written to disk, so queued messages survive a restart
            # (needs a durable queue too).
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        # The default exchange routes by queue name: the simplest point-to-point
        # setup. Use a topic/fanout exchange to reach several queues.
        await self._channel.default_exchange.publish(message, routing_key=self.queue_name)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        # process(): ack when the block succeeds; on an exception the message
        # is rejected (requeue=False by default), so a poison message cannot
        # loop forever. Configure a dead-letter exchange to keep such messages.
        async with message.process():
            self.received.append(
                {"text": message.body.decode(), "received_at": datetime.now(UTC).isoformat()}
            )
