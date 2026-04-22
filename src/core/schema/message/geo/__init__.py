from uuid import UUID
from pydantic import BaseModel, Field
from core.schema.message.core import MQEvent, MQRequest

class AddressData(MQRequest):
    id: UUID
    name: str = Field(max_length=512)

class AddressCreatedEvent(MQEvent[AddressData]): ...

class AddressUpdatedEvent(AddressCreatedEvent): ...

class AddressDelete(MQRequest):
    id: UUID

class AddressDeletedEvent(MQEvent[AddressDelete]): ...

class LocationData(MQRequest):
    id: UUID
    name: str = Field(max_length=512)

class LocationCreatedEvent(MQEvent[LocationData]): ...

class LocationUpdatedEvent(LocationCreatedEvent): ...

class LocationDelete(MQRequest):
    id: UUID

class LocationDeletedEvent(MQEvent[LocationDelete]): ...
