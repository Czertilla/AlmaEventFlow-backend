from typing import Generic, TypeVar
from uuid import UUID
from core.service.base import BaseService, required_transaction
from core.uow.event.person import PersonAUOW
from core.schema.message.profile import PersonData, PersonDelete

UOW = TypeVar("UOW", bound=PersonAUOW)


class PersonEventService(BaseService[UOW], Generic[UOW]):
    @required_transaction
    async def _create(self, person: PersonData):
        await self.uow.persons.add_n_return(data=person.model_dump())

    @required_transaction
    async def _upsert(self, person: PersonData):
        await self.uow.persons.upsert(data=person.model_dump())

    @required_transaction
    async def _delete(self, person_id: UUID):
        await self.uow.persons.delete_one(person_id)

    async def create(self, persons: list[PersonData]) -> None:
        async with self.uow as uow:
            for person in persons:
                await self._create(person)
            await uow.commit()

    async def update(self, persons: list[PersonData]) -> None:
        async with self.uow as uow:
            for person in persons:
                await self._upsert(person)
            await uow.commit()

    async def delete(self, persons: list[PersonDelete]) -> None:
        async with self.uow as uow:
            for person in persons:
                await self._delete(person.id)
            await uow.commit()
