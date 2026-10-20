from enum import StrEnum
from uuid import UUID


class PersonLinkAction(StrEnum):
    LINKED = "linked"
    REPLACED = "replaced"
    UNLINKED = "unlinked"

    @classmethod
    def of(
        cls, old_person_id: UUID | None, new_person_id: UUID | None
    ) -> "PersonLinkAction":
        if old_person_id is None:
            return cls.LINKED
        if new_person_id is None:
            return cls.UNLINKED
        return cls.REPLACED
