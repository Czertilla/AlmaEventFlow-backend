from logging import getLogger
from profile.dto.contact import (
    ContactCreateDTO,
    ContactDTO,
    ContactFilterDTO,
    ContactPatchDTO,
    ContactPutDTO,
)
from profile.exc.contact import (
    ContactNotExistsException,
    ContactOwnershipException,
)
from profile.exc.person import PersonNotExistsException
from profile.filter.contact import ContactFilter
from profile.models.contact import ContactORM
from profile.uow.contact import ContactUOW
from profile.uow.person import PersonContactUOW
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


class ContactService(BaseService[ContactUOW | PersonContactUOW]):
    @staticmethod
    def _to_dto(contact: ContactORM) -> ContactDTO:
        return dto_from_orm(contact, ContactDTO)

    @required_transaction
    async def _create(self, contact_create: ContactCreateDTO) -> ContactORM:
        if not await self.uow.persons.exists_id(contact_create.person_id):
            raise PersonNotExistsException()
        return await self.uow.contacts.add_n_return(dto_dict(contact_create))

    @required_transaction
    async def _read(self, contact_id: UUID) -> ContactORM:
        contact = await self.uow.contacts.get_by_id(contact_id)
        if contact is None:
            raise ContactNotExistsException()
        return contact

    @required_transaction
    async def _update(
        self,
        contact_id: UUID,
        contact_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> ContactORM:
        contact = await self.uow.contacts.update_one(contact_id, contact_data, flush)
        if contact is None:
            raise ContactNotExistsException()
        return contact

    @required_transaction
    async def _check_ownership(self, contact_id: UUID, person_id: UUID):
        exists = await self.uow.contacts.get_by_id(contact_id)
        if exists and exists.person_id != person_id:
            raise ContactOwnershipException()

    @required_transaction
    async def _upsert(self, contact_put: ContactPutDTO) -> ContactORM:
        await self._check_ownership(contact_put.id, contact_put.person_id)
        contact = await self.uow.contacts.upsert(dto_dict(contact_put))
        if contact is None:
            raise ContactNotExistsException()
        return contact

    @required_transaction
    async def _delete(self, contact_id: UUID) -> None:
        await self.uow.contacts.delete_one(contact_id)

    async def create(self, contact_create: ContactCreateDTO) -> ContactDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(contact_create))
            await uow.commit()
        return result

    async def read(self, contact_id: UUID) -> ContactDTO:
        async with self.uow:
            return self._to_dto(await self._read(contact_id))

    async def search(
        self,
        filter: ContactFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[ContactDTO]:
        async with self.uow as uow:
            contacts, total = await uow.contacts.search(
                ContactFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(contact) for contact in contacts],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def search_by_person(
        self,
        person_id: UUID,
        filter: ContactFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[ContactDTO]:
        async with self.uow as uow:
            contacts, total = await uow.contacts.search(
                ContactFilter.from_dto(filter),
                page_params,
                scope=[ContactORM.person_id == person_id],
            )
            return PageDTO(
                items=[self._to_dto(contact) for contact in contacts],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, contact_patch: ContactPatchDTO) -> ContactDTO:
        async with self.uow as uow:
            contact_data = dto_dict(contact_patch, only_set=True, exclude={"id"})
            result = self._to_dto(await self._update(contact_patch.id, contact_data))
            await uow.commit()
        return result

    async def put(self, contact_put: ContactPutDTO) -> ContactDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(contact_put))
            await uow.commit()
        return result

    async def delete(self, contact_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(contact_id)
            await uow.commit()

    async def check_ownership(self, contact_id: UUID, profile_id: UUID) -> None:
        async with self.uow:
            await self._check_ownership(contact_id, profile_id)
