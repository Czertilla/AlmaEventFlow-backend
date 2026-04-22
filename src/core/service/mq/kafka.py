from uuid import UUID, uuid4
from datetime import datetime
from typing import Any, TypeVar
from pydantic import BaseModel
from faststream.kafka import KafkaPublisher
from core.broker.kafka import broker
from core.mq.schema.eda.person import (
    PersonCreatedEvent,
    PersonUpdatedEvent,
    PersonDeletedEvent,
)
from core.enum.kafka import PersonTopic

T = TypeVar("T", bound=BaseModel)


class KafkaEventService:
    def __init__(self):
        self.broker = broker
    
    async def publish_event(self, topic: str, event: T) -> None:
        """Публикация события в Kafka"""
        publisher: KafkaPublisher = self.broker.publisher(topic)
        await publisher.publish(event.model_dump())
    
    async def publish_person_created(self, person_id: UUID, data: dict[str, Any]) -> None:
        """Публикация события создания персоны"""
        event = PersonCreatedEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            person_id=person_id,
            data=data
        )
        await self.publish_event(PersonTopic.CREATED, event)
    
    async def publish_person_updated(self, person_id: UUID, data: dict[str, Any]) -> None:
        """Публикация события обновления персоны"""
        event = PersonUpdatedEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            person_id=person_id,
            data=data
        )
        await self.publish_event(PersonTopic.UPDATED, event)
    
    async def publish_person_deleted(self, person_id: UUID) -> None:
        """Публикация события удаления персоны"""
        event = PersonDeletedEvent(
            event_id=uuid4(),
            timestamp=datetime.utcnow(),
            person_id=person_id
        )
        await self.publish_event(PersonTopic.DELETED, event)