from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectiveRefDTO:
    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class ChatBindingDTO:
    collective_id: UUID
    chat_id: int
    thread_id: int | None
    set_by_id: int
    announce_enabled: bool = True
    silent: bool = False
    pin_announcements: bool = False
    detailed_updates: bool = False
    language: str | None = None


@dataclass(frozen=True, slots=True)
class SetupResultDTO:
    binding: ChatBindingDTO
    collective_name: str
    changed: bool
    moved_from_chat_id: int | None = None


@dataclass(frozen=True, slots=True)
class ChatInfoDTO:
    title: str | None
    bot_is_admin: bool
