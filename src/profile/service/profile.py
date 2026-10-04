from logging import getLogger
from profile.dto.diet import DietDTO
from profile.dto.organization import OrganizationDTO
from profile.dto.person import PersonDTO
from profile.dto.profile import (
    ProfileCreateDTO,
    ProfileDTO,
    ProfileFilterDTO,
    ProfilePatchDTO,
    ProfilePutDTO,
)
from profile.exc.profile import ProfileNotExistsException
from profile.filter.profile import ProfileFilter
from profile.models.profile import ProfileORM
from profile.uow.profile import ProfileExtendedUOW
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


def profile_to_dto(profile: ProfileORM) -> ProfileDTO:
    person = profile.person
    diet = profile.diet
    workplace = profile.workplace
    return ProfileDTO(
        id=profile.id,
        birthdate=profile.birthdate,
        workplace_id=profile.workplace_id,
        diet_id=profile.diet_id,
        created_at=profile.created_at,
        edited_at=profile.edited_at,
        person=dto_from_orm(person, PersonDTO) if person else None,
        diet=dto_from_orm(diet, DietDTO) if diet else None,
        workplace=dto_from_orm(workplace, OrganizationDTO) if workplace else None,
    )


class ProfileService(BaseService[ProfileExtendedUOW]):
    @staticmethod
    def _to_dto(profile: ProfileORM) -> ProfileDTO:
        return profile_to_dto(profile)

    @required_transaction
    async def _create(self, profile_create: ProfileCreateDTO) -> ProfileORM:
        return await self.uow.profiles.add_n_return(dto_dict(profile_create))

    @required_transaction
    async def _put(self, profile_put: ProfilePutDTO) -> ProfileORM:
        profile = await self.uow.profiles.upsert(dto_dict(profile_put))
        if profile is None:
            raise ProfileNotExistsException()
        return profile

    @required_transaction
    async def _read(self, profile_id: UUID) -> ProfileORM:
        profile = await self.uow.profiles.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotExistsException()
        return profile

    @required_transaction
    async def _ensure_existance(self, profile_id: UUID):
        if not await self.uow.profiles.exists_id(profile_id):
            raise ProfileNotExistsException()

    @required_transaction
    async def _update(
        self,
        profile_id: UUID,
        profile_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> ProfileORM:
        profile = await self.uow.profiles.update_one(profile_id, profile_data, flush)
        if profile is None:
            raise ProfileNotExistsException()
        return profile

    @required_transaction
    async def _delete(self, profile_id: UUID) -> None:
        await self.uow.profiles.delete_one(profile_id)

    async def create(self, profile_create: ProfileCreateDTO) -> ProfileDTO:
        async with self.uow as uow:
            created = await self._create(profile_create)
            result = self._to_dto(await self._read(created.id))
            await uow.commit()
        return result

    async def read(self, profile_id: UUID) -> ProfileDTO:
        async with self.uow:
            return self._to_dto(await self._read(profile_id))

    async def search(
        self,
        filter: ProfileFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[ProfileDTO]:
        async with self.uow as uow:
            profiles, total = await uow.profiles.search(
                ProfileFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(profile) for profile in profiles],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, profile_patch: ProfilePatchDTO) -> ProfileDTO:
        async with self.uow as uow:
            profile_data = dto_dict(profile_patch, only_set=True, exclude={"id"})
            updated = await self._update(profile_patch.id, profile_data)
            result = self._to_dto(await self._read(updated.id))
            await uow.commit()
        return result

    async def put(self, profile_put: ProfilePutDTO) -> ProfileDTO:
        async with self.uow as uow:
            upserted = await self._put(profile_put)
            result = self._to_dto(await self._read(upserted.id))
            await uow.commit()
        return result

    async def delete(self, profile_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(profile_id)
            await uow.commit()

    async def ensure_existance(self, profile_id: UUID) -> None:
        async with self.uow:
            await self._ensure_existance(profile_id)
