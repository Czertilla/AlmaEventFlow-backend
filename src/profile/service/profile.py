from logging import getLogger
from uuid import UUID

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction
from profile.exc.profile import ProfileNotExistsException
from profile.models.profile import ProfileORM
from profile.schema.profile import (
    ProfileCreate,
    ProfilePatch,
    ProfilePut,
    ProfileRead,
)
from profile.uow.profile import ProfileExtendedUOW


logger = getLogger(__name__)


class ProfileService(BaseService[ProfileExtendedUOW]):
    @required_transaction
    async def _create(self, profile_create: ProfileCreate) -> ProfileORM:
        return await self.uow.profiles.add_n_return(profile_create.model_dump())

    @required_transaction
    async def _put(self, profile_put: ProfilePut) -> ProfileORM:
        return await self.uow.profiles.upsert(profile_put.model_dump())

    @required_transaction
    async def _read(self, profile_id: UUID) -> ProfileORM | None:
        profile = await self.uow.profiles.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotExistsException()
        return profile

    @required_transaction
    async def _ensure_existance(self, profile_id: UUID):
        if not self.uow.profiles.exists_id(profile_id):
            raise ProfileNotExistsException()

    @required_transaction
    async def _update(
        self, profile_id: UUID, profile_data: dict, *, flush: bool = False
    ) -> ProfileORM:
        profile = await self.uow.profiles.update_one(
            profile_id, profile_data, flush
        )
        if profile is None:
            raise ProfileNotExistsException()
        return profile

    async def create(self, profile_create: ProfileCreate) -> ProfileRead:
        async with self.uow as uow:
            result = ProfileRead.model_validate(
                await self._create(profile_create)
            )
            await uow.commit()
        return result

    async def read(self, profile_id: UUID) -> ProfileRead:
        async with self.uow:
            profile = await self._read(profile_id)
            return ProfileRead.model_validate(profile)

    async def read_many(
        self, page_params: SPageParam = SPageParam()
    ) -> SPage[ProfileRead]:
        async with self.uow as uow:
            profiles, total = await uow.profiles.get_many_cron(
                limit=page_params.limit,
                offset=page_params.offset,
            )
            return SPage(
                items=[
                    ProfileRead.model_validate(profile) for profile in profiles
                ],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, profile_patch: ProfilePatch) -> ProfileRead:
        async with self.uow as uow:
            profile_data = profile_patch.model_dump()
            result = ProfileRead.model_validate(
                await self._update(profile_data.pop("id"), profile_data)
            )
            await uow.commit()
        return result

    async def put(self, profile_put: ProfilePut) -> ProfileRead:
        async with self.uow as uow:
            result = ProfileRead.model_validate(await self._put(profile_put))
            await uow.commit()
        return result

    async def delete(self, profile_id: UUID) -> None:
        async with self.uow as uow:
            await self.uow.profiles.delete_one(profile_id)
            await uow.commit()

    async def ensure_existance(self, profile_id: UUID) -> None:
        async with self.uow:
            await self._ensure_existance(profile_id)
