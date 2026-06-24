from core.enum.notify import TransportTypeEnum

from notify.transport.base import BaseTransport
from notify.transport.email import EmailTransport
from notify.transport.webpush import WebPushTransport

_TRANSPORTS: dict[TransportTypeEnum, BaseTransport] = {
    transport.type: transport
    for transport in (
        EmailTransport(),
        WebPushTransport(),
    )
}

GUARANTEED: TransportTypeEnum = TransportTypeEnum.email
DEFAULT_ENABLED: frozenset[TransportTypeEnum] = frozenset(
    {TransportTypeEnum.email})


def get(transport_type: TransportTypeEnum) -> BaseTransport | None:
    return _TRANSPORTS.get(transport_type)


def all_transports() -> list[BaseTransport]:
    return list(_TRANSPORTS.values())
