from uuid import UUID
from pydantic import BaseModel, Field
from core.schema.message.core import MQEvent, MQRequest


class PersonData(MQRequest):
    id: UUID
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128)


class PersonCreatedEvent(MQEvent[PersonData]): ...


class PersonUpdatedEvent(PersonCreatedEvent): ...


class PersonDelete(MQRequest):
    id: UUID


class PersonDeletedEvent(MQEvent[PersonDelete]): ...
