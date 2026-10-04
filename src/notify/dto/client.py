from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from core.enum.notify import TransportTypeEnum


@dataclass(frozen=True, slots=True)
class ClientCreateDTO:
    endpoint: str
    transport: TransportTypeEnum = TransportTypeEnum.webpush
    label: str | None = None
    payload: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClientDTO:
    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    label: str | None
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClientTargetDTO:
    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    payload: dict[str, str] = field(default_factory=dict)
