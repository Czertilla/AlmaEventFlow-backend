from typing import Awaitable, TypeVar

from core.broker.kafka import broker
from core.schema.message.core import MQError, MQRequest, MQResponse
from core.utils.exc.http import VancedHTTPException

T = TypeVar("T")


class RpcError(Exception):
    def __init__(self, error: MQError) -> None:
        super().__init__(error.detail)
        self.error = error


async def rpc_call(
    topic: str, request: MQRequest, response_model: type[T], *, timeout: float = 5.0
) -> T:
    raw = await broker.request(request, topic, timeout=timeout)
    if hasattr(raw, "body"):
        body = raw.body
        if isinstance(body, (bytes, str)):
            response = MQResponse[response_model].model_validate_json(body)
        else:
            response = MQResponse[response_model].model_validate(body)
    else:
        # Monolith broker: the handler's MQResponse comes back as-is, already
        # holding a real response_model instance for `.data` — no reparsing.
        response = raw
    if response.error is not None:
        raise RpcError(response.error)
    return response.data


async def rpc_respond(coro: Awaitable[T]) -> MQResponse[T]:
    try:
        return MQResponse(data=await coro)
    except VancedHTTPException as exc:
        return MQResponse(
            data=None,
            error=MQError(code=exc.status_code, detail=str(exc.detail), extra={}),
        )
