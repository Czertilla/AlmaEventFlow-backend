from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class PersonCreatedEvent(BaseModel):
    """Событие создания персоны"""
    event_type: str = "person.created"
    event_id: UUID
    timestamp: datetime
    person_id: UUID
    data: dict


class PersonUpdatedEvent(BaseModel):
    """Событие обновления персоны"""
    event_type: str = "person.updated"
    event_id: UUID
    timestamp: datetime
    person_id: UUID
    data: dict


class PersonDeletedEvent(BaseModel):
    """Событие удаления персоны"""
    event_type: str = "person.deleted"
    event_id: UUID
    timestamp: datetime
    person_id: UUID