from uuid import UUID

from pydantic import BaseModel, Field

from core.schema.message.core import MQEvent, MQRequest


class PersonData(MQRequest):
    id: UUID
    surname: str = Field(max_length=128)
    name: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128)


class PersonCreatedEvent(MQEvent[PersonData]): ...


class PersonUpdatedEvent(PersonCreatedEvent): ...


class PersonLinkData(MQRequest):
    user_id: UUID
    person_id: UUID | None = Field(
        description="The person the account stands for now, none when it has no one."
    )


class PersonLinkChangedEvent(MQEvent[PersonLinkData]): ...


class LinkAccountRequest(MQRequest):
    user_id: UUID
    person_id: UUID
    replace: bool = False


class PersonDelete(MQRequest):
    id: UUID


class PersonDeletedEvent(MQEvent[PersonDelete]): ...
