import asyncio
from functools import lru_cache
from faststream.kafka import (
    KafkaBroker as BaseKafkaBroker,
    KafkaRouter as BaseKafkaRouter,
)
from faststream.kafka.fastapi import KafkaRouter as BaseKafkaStreamRouter
from core.config.settings import settings
from logging import getLogger

logger = getLogger(__name__)


if not settings.IN_MEMORY_BROKER:

    def kafka_uri(
        host: str = settings.KAFKA_HOST,
        port: str = settings.KAFKA_PORT,
    ):
        logger.info(f"Kafka URI configuration: host={host}, port={port}")
        return f"{host}:{port}"

    def _connection_kwargs() -> dict:
        kwargs: dict = {}
        if settings.KAFKA_SECURITY_PROTOCOL:
            kwargs["security_protocol"] = settings.KAFKA_SECURITY_PROTOCOL
        return kwargs

    class KafkaBroker(BaseKafkaBroker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reconnect_interval = 0.8

        async def start(self) -> None:
            try:
                logger.info(
                    f"Attempting to connect to Kafka with servers: {self.settings.servers}"
                )
                await super().start()
            except Exception as e:
                logger.error(
                    "Error starting broker, reconnecting in "
                    f"{self.reconnect_interval} seconds ({e=})"
                )
                await asyncio.sleep(self.reconnect_interval)
                self.reconnect_interval *= 2
                await self.start()

    class KafkaStreamRouter(BaseKafkaStreamRouter):
        def __init__(self, url: str = kafka_uri(), *args, **kwargs):
            logger.info(f"KafkaStreamRouter initializing with URL: {url}")
            super().__init__(url, *args, **{**_connection_kwargs(), **kwargs})

    class KafkaRouter(BaseKafkaRouter):
        def __init__(self, *args, **kwargs):
            logger.info("KafkaRouter initializing")
            super().__init__(*args, **kwargs)

        def subscriber(self, *args, **kwargs):
            """Injects the configured consumer group when the caller did not set
            one and ``KAFKA_CONSUMER_GROUP`` is configured."""
            if settings.KAFKA_CONSUMER_GROUP and "group_id" not in kwargs:
                kwargs["group_id"] = settings.KAFKA_CONSUMER_GROUP
            return super().subscriber(*args, **kwargs)

    @lru_cache
    def geStreamRouter() -> KafkaStreamRouter:
        uri = kafka_uri()
        logger.info(f"Creating KafkaStreamRouter with URI: kafka://{uri}")
        return KafkaStreamRouter(url=uri)

else:
    from core.broker.local import (
        MonolithBroker as KafkaBroker,  # noqa: F401
        MonolithRouter as KafkaRouter,  # noqa: F401
        MonolithStreamRouter as KafkaStreamRouter,
    )

    @lru_cache
    def geStreamRouter() -> KafkaStreamRouter:
        logger.warning("MONOLITE=True, using in-process event transport")
        return KafkaStreamRouter()


@lru_cache
def getBroker():
    return geStreamRouter().broker


stream_router = geStreamRouter()
broker = getBroker()
