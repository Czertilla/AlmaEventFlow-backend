from logging import getLogger
from uuid import UUID

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from profile.api.kafka.pub.person import (
    on_person_created,
    on_person_deleted,
    on_person_updated,
)
from profile.exc.person import PersonNotExistsException
from profile.filter.person import PersonFilter
from profile.models.person import PersonORM
from profile.schema.person import (
    PersonCreate,
    PersonItemRead,
    PersonPatch,
    PersonPut,
    PersonRead,
)
from profile.uow.person import PersonUOW


logger = getLogger(__name__)


class PersonService(BaseService[PersonUOW]):
    @required_transaction
    async def _create(self, person_create: PersonCreate) -> PersonORM:
        return await self.uow.persons.add_n_return(person_create.model_dump())

    @required_transaction
    async def _ensure_existance(self, person_id: UUID):
        if not self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()

    @required_transaction
    async def _read(
        self, person_id: UUID, with_main_contacts: bool = False
    ) -> PersonORM | None:
        person = (
            await self.uow.persons.get_with_contacts(person_id)
            if with_main_contacts
            else await self.uow.persons.get_by_id(person_id)
        )
        if person is None:
            raise PersonNotExistsException()
        return person

    @required_transaction
    async def _update(
        self, person_id: UUID, person_data: dict, *, flush: bool = False
    ) -> PersonORM:
        person = await self.uow.persons.update_one(
            person_id, person_data, flush
        )
        if person is None:
            raise PersonNotExistsException()
        return person

    @required_transaction
    async def _upsert(self, person_put: PersonPut) -> PersonORM:
        person = await self.uow.persons.upsert(person_put.model_dump())
        return person

    @required_transaction
    async def _delete(self, person_id: UUID) -> None:
        await self.uow.persons.delete_one(person_id)

    async def create(self, person_create: PersonCreate) -> PersonRead:
        async with self.uow as uow:
            person = await self._create(person_create)
            result = PersonRead.model_validate(person)
            await uow.commit()
        await on_person_created([person])
        return result

    async def read(self, person_id: UUID) -> PersonRead:
        async with self.uow:
            return PersonRead.model_validate(await self._read(person_id, True))

    async def search(
        self, filter: PersonFilter, page_params: SPageParam = SPageParam()
    ) -> SPage[PersonItemRead]:
        async with self.uow as uow:
            persons, total = await uow.persons.search(filter, page_params)
            return SPage(
                items=[
                    PersonItemRead.model_validate(person) for person in persons
                ],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, person_patch: PersonPatch) -> PersonRead:
        async with self.uow as uow:
            person_data = person_patch.model_dump()
            person = await self._update(person_data.pop("id"), person_data)
            result = PersonRead.model_validate(person)
            await uow.commit()
        await on_person_updated([person])
        return result

    async def put(self, person_put: PersonPut) -> PersonRead:
        async with self.uow as uow:
            person = await self._upsert(person_put)
            result = PersonRead.model_validate(person)
            await uow.commit()
        await on_person_updated([person])
        return result

    async def delete(self, person_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(person_id)
            await uow.commit()
        await on_person_deleted([person_id])
