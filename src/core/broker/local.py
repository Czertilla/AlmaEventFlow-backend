from asyncio import Task, create_task, iscoroutine
from collections import defaultdict
from collections.abc import Awaitable, Callable
from functools import wraps
from inspect import signature
from logging import getLogger
from typing import Any, TypeVar

from fastapi.params import Depends as FastAPIDepends
from faststream import apply_types

from core.utils.mixin.singleton import SingletonMixin

logger = getLogger()

Handler = Callable[[Any], Awaitable[Any]]
HandlerT = TypeVar("HandlerT", bound=Callable[..., Awaitable[Any]])


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
    # apply_types() resolves only faststream.Depends, subscribers use fastapi's
    sig = signature(func)
    depends_names = [
        name for name, param in sig.parameters.items()
        if isinstance(param.default, FastAPIDepends)
    ]
    if not depends_names:
        return func

    @wraps(func)
    async def bound(*args: Any, **kwargs: Any):
        cache: dict[int, Any] = {}
        for name in depends_names:
            kwargs[name] = await _resolve_fastapi_dependency(
                sig.parameters[name].default.dependency, cache
            )
        return await func(*args, **kwargs)

    bound.__signature__ = sig.replace(  # pyright: ignore[reportAttributeAccessIssue]
        parameters=[p for p in sig.parameters.values() if p.name not in depends_names]
    )
    return bound


class MonolithBroker(SingletonMixin):
    def __init__(self) -> None:
        # the singleton's __init__ runs on every construction: keep the handlers
        if not hasattr(self, "_handlers"):
            self._handlers: dict[str, list[Handler]] = defaultdict(list)
            self._tasks: set[Task[None]] = set()

    async def start(self) -> None:
        logger.info("Monolith broker started")
        return None

    def subscriber(
        self, topic: str, *args: Any, **kwargs: Any
    ) -> Callable[[HandlerT], HandlerT]:
        def decorator(func: HandlerT) -> HandlerT:
            wrapped = apply_types(_bind_fastapi_depends(func))
            self._handlers[topic].append(wrapped)
            logger.info(
                "Registered monolith subscriber: topic=%s handler=%s",
                topic,
                func.__name__,
            )
            return func

        return decorator

    def publisher(
        self, topic: str, *args: Any, **kwargs: Any
    ) -> Callable[[HandlerT], HandlerT]:
        def decorator(func: HandlerT) -> HandlerT:
            return func

        return decorator

    async def publish(self, message: Any, topic: str, *args: Any, **kwargs: Any):
        handlers = self._handlers.get(topic, [])
        if not handlers and topic.endswith(".dlq"):
            logger.error(
                "Monolith dead letter: topic=%s message=%r", topic, message
            )
            return
        if not handlers:
            logger.warning(
                "Monolith publish: no subscribers for topic=%s, message "
                "dropped (the consumer runs in another process or is not "
                "registered here)",
                topic,
            )
            return
        logger.info("Monolith publish: topic=%s message=%r", topic, message)
        for handler in handlers:
            task = create_task(self._dispatch(handler, message, topic))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _dispatch(handler: Handler, message: Any, topic: str) -> None:
        try:
            await handler(message)
        except Exception:
            logger.exception(
                "Monolith subscriber failed: topic=%s handler=%s",
                topic,
                getattr(handler, "__name__", handler),
            )

    async def request(
        self,
        message: Any,
        topic: str,
        *args: Any,
        timeout: float = 5.0,  # noqa: ASYNC109  # same keyword as the faststream broker
        **kwargs: Any,
    ) -> Any:
        handlers = self._handlers.get(topic, [])
        if len(handlers) != 1:
            raise RuntimeError(
                f"RPC topic {topic!r} has {len(handlers)} responders, "
                "expected exactly 1"
            )
        return await handlers[0](message)


class MonolithRouter:
    def __init__(self, broker: MonolithBroker | None = None):
        self.broker = broker if broker is not None else MonolithBroker()

    def subscriber(
        self, topic: str, *args: Any, **kwargs: Any
    ) -> Callable[[HandlerT], HandlerT]:
        return self.broker.subscriber(topic, *args, **kwargs)

    def publisher(
        self, topic: str, *args: Any, **kwargs: Any
    ) -> Callable[[HandlerT], HandlerT]:
        return self.broker.publisher(topic, *args, **kwargs)

    def include_router(self, *args: Any, **kwargs: Any): ...


class MonolithStreamRouter:
    def __init__(self) -> None:
        self.broker = MonolithBroker()

    def subscriber(
        self, topic: str, *args: Any, **kwargs: Any
    ) -> Callable[[HandlerT], HandlerT]:
        return self.broker.subscriber(topic, *args, **kwargs)
