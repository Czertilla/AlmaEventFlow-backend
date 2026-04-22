from asyncio import create_task
from collections import defaultdict
from logging import getLogger
from typing import Any, Awaitable, Callable
from faststream import apply_types

from core.utils.mixin.singleton import SingletonMixin

logger = getLogger()

Handler = Callable[[Any], Awaitable[Any]]


class MonolithBroker(SingletonMixin):
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    async def start(self) -> None:
        logger.info("Monolith broker started")
        return None

    def subscriber(self, topic: str, *args, **kwargs):
        def decorator(func: Handler):
            wrapped = apply_types(func)
            self._handlers[topic].append(wrapped)
            logger.info(
                "Registered monolith subscriber: topic=%s handler=%s",
                topic,
                func.__name__,
            )
            return func

        return decorator

    def publisher(self, topic: str, *args, **kwargs):
        def decorator(func: Handler):
            return func

        return decorator

    async def publish(self, message: Any, topic: str, *args, **kwargs):
        logger.info("Monolith publish: topic=%s message=%r", topic, message)
        for handler in self._handlers.get(topic, []):
            create_task(handler(message))


class MonolithRouter:
    def __init__(self, broker: MonolithBroker = MonolithBroker()):
        self.broker = broker

    def subscriber(self, topic: str, *args, **kwargs):
        return self.broker.subscriber(topic, *args, **kwargs)

    def publisher(self, topic: str, *args, **kwargs):
        return self.broker.publisher(topic, *args, **kwargs)

    def include_router(self, *args, **kwargs): ...


class MonolithStreamRouter:
    def __init__(self) -> None:
        self.broker = MonolithBroker()

    def subscriber(self, topic: str, *args, **kwargs):
        return self.broker.subscriber(topic, *args, **kwargs)
