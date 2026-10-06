from dataclasses import dataclass
from enum import StrEnum, auto
from uuid import UUID

from bot.tg.dto.collective_chat import CollectiveRefDTO


class ActorState(StrEnum):
    unlinked = auto()
    linked = auto()
    member = auto()
    leader = auto()


@dataclass(frozen=True, slots=True)
class ActorDTO:
    tg_id: int
    person_id: UUID | None = None
    is_superuser: bool = False
    led: tuple[CollectiveRefDTO, ...] = ()
    member_of: tuple[CollectiveRefDTO, ...] = ()
    roles_known: bool = True

    @property
    def is_linked(self) -> bool:
        return self.person_id is not None

    @property
    def is_leader(self) -> bool:
        return bool(self.led)

    @property
    def state(self) -> ActorState:
        if self.person_id is None:
            return ActorState.unlinked
        if self.led:
            return ActorState.leader
        if self.member_of:
            return ActorState.member
        return ActorState.linked

    def leads(self, collective_id: UUID) -> bool:
        return any(item.id == collective_id for item in self.led)

    def led_collective(self, collective_id: UUID) -> CollectiveRefDTO | None:
        return next((i for i in self.led if i.id == collective_id), None)
