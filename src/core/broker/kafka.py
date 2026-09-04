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
from faststream.kafka.security import parse_security
from faststream.security import (
    BaseSecurity,
    SASLPlaintext,
    SASLScram256,
    SASLScram512,
)

from core.broker.kafka_rpc import KafkaRpcReplyConsumer
from core.config.settings import settings

logger = getLogger(__name__)


if not settings.IN_MEMORY_BROKER:

    def kafka_uri(
        host: str = settings.KAFKA_HOST,
        port: str = settings.KAFKA_PORT,
    ):
        logger.info(f"Kafka URI configuration: host={host}, port={port}")
        return f"{host}:{port}"

    _SASL_MECHANISMS = {
        "PLAIN": SASLPlaintext,
        "SCRAM-SHA-256": SASLScram256,
        "SCRAM-SHA-512": SASLScram512,
    }

    def _wants_tls(protocol: str) -> bool:
        if protocol in {"SSL", "SASL_SSL"}:
            return True
        if protocol in {"PLAINTEXT", "SASL_PLAINTEXT"}:
            return False
        # Unset protocol: preserve plaintext-by-default, only opting into TLS
        # when a CA was actually configured (legacy KAFKA_SSL_CA behavior).
        return settings.KAFKA_SSL_CA is not None

    def _ssl_context(protocol: str) -> ssl.SSLContext | None:
        if not _wants_tls(protocol):
            return None
        ca = settings.KAFKA_SSL_CA
        # No custom CA configured: fall back to the system trust store, which is
        # what a publicly-trusted (e.g. Let's Encrypt) broker certificate needs.
        context = (
            ssl.create_default_context(cafile=ca)
            if ca
            else ssl.create_default_context()
        )
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

        if settings.KAFKA_SASL_USERNAME and settings.KAFKA_SASL_PASSWORD:
            mechanism = (settings.KAFKA_SASL_MECHANISM or "SCRAM-SHA-256").upper()
            security_cls = _SASL_MECHANISMS.get(mechanism)
            if security_cls is None:
                raise ValueError(
                    "KAFKA_SASL_MECHANISM=%r is not supported; choose one of %s"
                    % (settings.KAFKA_SASL_MECHANISM, ", ".join(_SASL_MECHANISMS))
                )
            use_ssl = protocol != "SASL_PLAINTEXT"
            return security_cls(
                settings.KAFKA_SASL_USERNAME,
                settings.KAFKA_SASL_PASSWORD.get_secret_value(),
                ssl_context=_ssl_context(protocol) if use_ssl else None,
                use_ssl=use_ssl,
            )

        context = _ssl_context(protocol)
        if not context and protocol not in {"", "SSL"}:
            raise ValueError(
                "KAFKA_SECURITY_PROTOCOL=%r is not supported; configure "
                "KAFKA_SSL_CA for TLS, KAFKA_SASL_USERNAME/PASSWORD for SASL, "
                "or leave it unset for PLAINTEXT" % settings.KAFKA_SECURITY_PROTOCOL
            )
        if context is None and protocol == "":
            return None
        return BaseSecurity(ssl_context=context, use_ssl=True)

    class KafkaBroker(BaseKafkaBroker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.reconnect_interval = 0.8
            # Real Kafka has no request/reply support in faststream out of the
            # box -- see core.broker.kafka_rpc for why and how this patches it in.
            self._rpc_reply = KafkaRpcReplyConsumer(
                bootstrap_servers=kafka_uri(),
                client_id=self.config.client_id or "aef",
                connect_kwargs=parse_security(_kafka_security()),
            )
            self._rpc_reply.attach(self.config.producer)

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

        async def stop(self, *args, **kwargs) -> None:
            await self._rpc_reply.stop()
            await super().stop(*args, **kwargs)

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
