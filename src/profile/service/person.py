from collections.abc import Collection
from logging import getLogger
from profile.api.kafka.pub.person import (
    on_person_created,
    on_person_deleted,
    on_person_link_changed,
    on_person_updated,
)
from profile.dto.person import (
    PersonCreateDTO,
    PersonDTO,
    PersonFilterDTO,
    PersonNameDTO,
    PersonPatchDTO,
    PersonPutDTO,
)
from profile.exc.person import PersonNotExistsException
from profile.filter.person import PersonFilter
from profile.models.person import PersonORM
from profile.uow.person import PersonUOW
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.enum.profile import PersonLinkSource
from core.schema.message.profile import PersonData, PersonLinkData
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


class PersonService(BaseService[PersonUOW]):
    @staticmethod
    def _to_dto(person: PersonORM) -> PersonDTO:
        return dto_from_orm(person, PersonDTO)

    @staticmethod
    def _event(person: PersonDTO) -> PersonData:
        return PersonData(
            id=person.id,
            surname=person.surname,
            name=person.name,
            patronymic=person.patronymic,
        )

    @required_transaction
    async def _create(self, person_create: PersonCreateDTO) -> PersonORM:
        return await self.uow.persons.add_n_return(dto_dict(person_create))

    @required_transaction
    async def _ensure_existance(self, person_id: UUID):
        if not await self.uow.persons.exists_id(person_id):
            raise PersonNotExistsException()

    @required_transaction
    async def _read(
        self, person_id: UUID, with_main_contacts: bool = False
    ) -> PersonORM:
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
        self,
        person_id: UUID,
        person_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> PersonORM:
        person = await self.uow.persons.update_one(person_id, person_data, flush)
        if person is None:
            raise PersonNotExistsException()
        return person

    @required_transaction
    async def _upsert(self, person_put: PersonPutDTO) -> PersonORM:
        person = await self.uow.persons.upsert(dto_dict(person_put))
        if person is None:
            raise PersonNotExistsException()
        return person

    @required_transaction
    async def _delete(self, person_id: UUID) -> None:
        await self.uow.persons.delete_one(person_id)

    async def create(self, person_create: PersonCreateDTO) -> PersonDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(person_create))
            await uow.commit()
        await on_person_created([self._event(result)])
        return result

    async def read(self, person_id: UUID) -> PersonDTO:
        async with self.uow:
            return self._to_dto(await self._read(person_id, True))

    async def names(
        self, requested: Collection[UUID], allowed: Collection[UUID]
    ) -> list[PersonNameDTO]:
        """One entry per requested id; the name is left out of an id that is not
        allowed or does not exist."""
        async with self.uow:
            known = {
                person.id: person for person in await self.uow.persons.by_ids(allowed)
            }
        return [
            PersonNameDTO(
                id=person_id,
                surname=person.surname if person else None,
                name=person.name if person else None,
                patronymic=person.patronymic if person else None,
            )
            for person_id in dict.fromkeys(requested)
            for person in [known.get(person_id)]
        ]

    async def search(
        self,
        filter: PersonFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
        *,
        only: Collection[UUID] | None = None,
    ) -> PageDTO[PersonDTO]:
        scope: list[ColumnElement[bool]] | None = (
            None if only is None else [PersonORM.id.in_(only)]
        )
        async with self.uow as uow:
            persons, total = await uow.persons.search(
                PersonFilter.from_dto(filter), page_params, scope=scope
            )
            return PageDTO(
                items=[self._to_dto(person) for person in persons],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, person_patch: PersonPatchDTO) -> PersonDTO:
        async with self.uow as uow:
            person_data = dto_dict(person_patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(person_patch.id, person_data))
            await uow.commit()
        await on_person_updated([self._event(result)])
        return result

    async def put(self, person_put: PersonPutDTO) -> PersonDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(person_put))
            await uow.commit()
        await on_person_updated([self._event(result)])
        return result

    async def delete(self, person_id: UUID, actor_id: UUID | None = None) -> None:
        async with self.uow as uow:
            link = await uow.account_links.get_by_person(person_id)
            user_id = link.user_id if link is not None else None
            await self._delete(person_id)
            if user_id is not None:
                await uow.account_history.record(
                    user_id,
                    old_person_id=person_id,
                    new_person_id=None,
                    source=PersonLinkSource.PERSON_DELETED,
                    actor_id=actor_id,
                )
            await uow.commit()
        if user_id is not None:
            await on_person_link_changed(
                [PersonLinkData(user_id=user_id, person_id=None)]
            )
        await on_person_deleted([person_id])
