from dataclasses import dataclass
from typing import Any, Protocol

from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest


class _ContentSource(Protocol):
    title: str
    body: str
    action_url: str | None
    category: NotificationCategory
    data: dict[str, Any]


@dataclass
class NotificationContent:
    """Normalized notification content for a single recipient."""

    title: str
    body: str
    action_url: str | None
    category: NotificationCategory
    data: dict[str, str]

    @classmethod
    def from_request(cls, request: NotificationRequest) -> "NotificationContent":
        return cls._from(request)

    @classmethod
    def from_model(cls, model: _ContentSource) -> "NotificationContent":
        return cls._from(model)

    @classmethod
    def _from(cls, source: _ContentSource) -> "NotificationContent":
        return cls(
            title=source.title,
            body=source.body,
            action_url=source.action_url,
            category=source.category,
            data=dict(source.data),
        )
