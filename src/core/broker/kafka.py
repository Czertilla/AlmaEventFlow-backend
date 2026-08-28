import asyncio
import ssl
from functools import lru_cache
from logging import getLogger

from faststream.kafka import (
    KafkaBroker as BaseKafkaBroker,
)
from faststream.kafka import (
    KafkaRouter as BaseKafkaRouter,
)
from faststream.kafka.fastapi import KafkaRouter as BaseKafkaStreamRouter
from faststream.security import BaseSecurity

from core.config.settings import settings

logger = getLogger(__name__)


if not settings.IN_MEMORY_BROKER:

    def kafka_uri(
        host: str = settings.KAFKA_HOST,
        port: str = settings.KAFKA_PORT,
    ):
        logger.info(f"Kafka URI configuration: host={host}, port={port}")
        return f"{host}:{port}"

    def _ssl_context() -> ssl.SSLContext | None:
        ca = settings.KAFKA_SSL_CA
        if ca is None:
            return None
        context = ssl.create_default_context(cafile=ca)
        # Pin to a single TLS version: the broker's JSSE stack sends a
        # handshake_failure alert against the version *range* an unpinned
        # default context offers, but accepts a ClientHello for exactly one
        # version (confirmed with both 1.2 and 1.3 individually).
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        if not settings.KAFKA_SSL_CHECK_HOSTNAME:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        if settings.KAFKA_SSL_CERT:
            context.load_cert_chain(
                settings.KAFKA_SSL_CERT,
                settings.KAFKA_SSL_KEY,
                settings.KAFKA_SSL_KEY_PASSWORD,
            )
        return context

    def _kafka_security() -> BaseSecurity | None:
        protocol = (settings.KAFKA_SECURITY_PROTOCOL or "").upper()
        context = _ssl_context()
        if not context and protocol not in {"", "SSL"}:
            raise ValueError(
                "KAFKA_SECURITY_PROTOCOL=%r is not supported; configure "
                "KAFKA_SSL_CA for TLS or leave it unset for PLAINTEXT"
                % settings.KAFKA_SECURITY_PROTOCOL
            )
        if context is None and protocol == "":
            return None
        return BaseSecurity(ssl_context=context, use_ssl=True)

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
        def __init__(
            self,
            url: str = kafka_uri(),
            security: BaseSecurity = _kafka_security(),
            *args,
            **kwargs,
        ):
            logger.info(f"KafkaStreamRouter initializing with URL: {url}")
            super().__init__(url, *args, security=security, **kwargs)

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
    )
    from core.broker.local import (
        MonolithRouter as KafkaRouter,  # noqa: F401
    )
    from core.broker.local import (
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
