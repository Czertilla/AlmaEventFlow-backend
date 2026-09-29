from asyncio import create_task, iscoroutine
from collections import defaultdict
from functools import wraps
from inspect import signature
from logging import getLogger
from typing import Any, Awaitable, Callable

from fastapi.params import Depends as FastAPIDepends
from faststream import apply_types

from core.utils.mixin.singleton import SingletonMixin

logger = getLogger()

Handler = Callable[[Any], Awaitable[Any]]


async def _resolve_fastapi_dependency(
    dependency: Callable[..., Any] | None, cache: dict[int, Any]
) -> Any:
    assert dependency is not None
    key = id(dependency)
    if key in cache:
        return cache[key]
    kwargs = {}
    for name, param in signature(dependency).parameters.items():
        if isinstance(param.default, FastAPIDepends):
            sub_dependency = param.default.dependency
            kwargs[name] = await _resolve_fastapi_dependency(sub_dependency, cache)
    result = dependency(**kwargs)
    if iscoroutine(result):
        result = await result
    cache[key] = result
    return result


def _bind_fastapi_depends(func: Handler) -> Handler:
    # apply_types() only resolves faststream.Depends, not fastapi.Depends -- which
    # every subscriber uses for FastAPI-mounted stream_router compatibility in prod.
    sig = signature(func)
    depends_names = [
        name for name, param in sig.parameters.items()
        if isinstance(param.default, FastAPIDepends)
    ]
    if not depends_names:
        return func

    @wraps(func)
    async def bound(*args, **kwargs):
        cache: dict[int, Any] = {}
        for name in depends_names:
            kwargs[name] = await _resolve_fastapi_dependency(
                sig.parameters[name].default.dependency, cache
            )
        return await func(*args, **kwargs)

    bound.__signature__ = sig.replace(  # type: ignore[attr-defined]
        parameters=[p for p in sig.parameters.values() if p.name not in depends_names]
    )
    return bound


class MonolithBroker(SingletonMixin):
    def __init__(self) -> None:
        # SingletonMixin.__new__ returns the same instance on every call, but
        # __init__ still runs again each time -- guard it, or a second
        # construction anywhere would silently wipe every already-registered
        # subscriber.
        if not hasattr(self, "_handlers"):
            self._handlers: dict[str, list[Handler]] = defaultdict(list)

    async def start(self) -> None:
        logger.info("Monolith broker started")
        return None

    def subscriber(self, topic: str, *args, **kwargs):
        def decorator(func: Handler):
            wrapped = apply_types(_bind_fastapi_depends(func))
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

    async def request(
        self, message: Any, topic: str, *args, timeout: float = 5.0, **kwargs
    ) -> Any:
        handlers = self._handlers.get(topic, [])
        if len(handlers) != 1:
            raise RuntimeError(
                f"RPC topic {topic!r} has {len(handlers)} responders, "
                "expected exactly 1"
            )
        return await handlers[0](message)


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
