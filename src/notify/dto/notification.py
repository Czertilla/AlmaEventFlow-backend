from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest

if TYPE_CHECKING:
    from notify.models.notification import NotificationORM


class _ContentSource(Protocol):
    title: str
    body: str
    action_url: str | None
    category: NotificationCategory
    data: dict[str, Any]


@dataclass(frozen=True, slots=True)
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
    def from_model(cls, model: "NotificationORM") -> "NotificationContent":
        return cls._from(cast("_ContentSource", model))

    @classmethod
    def _from(cls, source: _ContentSource) -> "NotificationContent":
        return cls(
            title=source.title,
            body=source.body,
            action_url=source.action_url,
            category=source.category,
            data=dict(source.data),
        )
