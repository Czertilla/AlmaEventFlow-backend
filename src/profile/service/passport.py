from logging import getLogger
from uuid import UUID

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from profile.exc.passport import (
    PassportNotExistsException,
    PassportOwnershipException,
)
from profile.filter.passport import PassportFilter
from profile.models.passport import PassportORM, NameVariantORM
from profile.schema.passport import (
    PassportCreate,
    PassportItemRead,
    PassportPatch,
    PassportPut,
    PassportRead,
    NameVariantCreate,
    NameVariantPatch,
    NameVariantPut,
    NameVariantRead,
)
from profile.uow.passport import PassportUOW
from profile.uow.profile import ProfilePassportUOW


logger = getLogger(__name__)


class PassportService(BaseService[PassportUOW | ProfilePassportUOW]):
    @required_transaction
    async def _create(self, passport_create: PassportCreate) -> PassportORM:
        passport_data = passport_create.model_dump()
        name_variant_data = passport_data.pop("name_variant", None)

        passport = await self.uow.passports.add_n_return(data=passport_data)

        if name_variant_data:
            name_variant_data["passport_id"] = passport.id
            await self.uow.name_variants.add_n_return(data=name_variant_data)

        return passport

    @required_transaction
    async def _check_ownership(self, passport_id: UUID, profile_id: UUID):
        exists = await self.uow.passports.get_by_id(passport_id)
        if exists and exists.profile_id != profile_id:
            raise PassportOwnershipException()

    @required_transaction
    async def _read(self, passport_id: UUID) -> PassportORM | None:
        passport = await self.uow.passports.get_by_id(passport_id)
        if passport is None:
            raise PassportNotExistsException()
        return passport

    @required_transaction
    async def _ensure_existance(self, passport_id: UUID):
        if not self.uow.passports.exists_id(passport_id):
            raise PassportNotExistsException()

    @required_transaction
    async def _update(
        self, passport_id: UUID, passport_data: dict, *, flush: bool = False
    ) -> PassportORM:
        passport = await self.uow.passports.update_one(
            passport_id, passport_data, flush
        )
        if passport is None:
            raise PassportNotExistsException()
        return passport

    @required_transaction
    async def _upsert(self, passport_put: PassportPut) -> PassportORM:
        await self._check_ownership(passport_put.id, passport_put.profile_id)
        return await self.uow.passports.upsert(passport_put.model_dump())

    @required_transaction
    async def _delete(self, passport_id: UUID) -> None:
        await self.uow.passports.delete_one(passport_id)

    async def create(self, passport_create: PassportCreate) -> PassportRead:
        async with self.uow as uow:
            result = PassportRead.model_validate(
                await self._create(passport_create)
            )
            await uow.commit()
        return result

    async def read(self, passport_id: UUID) -> PassportRead:
        async with self.uow:
            return PassportRead.model_validate(await self._read(passport_id))

    async def search_by_profile(
        self,
        profile_id: UUID,
        filter: PassportFilter,
        page_params: SPageParam = SPageParam(),
    ) -> SPage[PassportItemRead]:
        async with self.uow as uow:
            passports, total = await uow.passports.search(
                filter,
                page_params,
                scope=[PassportORM.profile_id == profile_id],
            )
            return SPage(
                items=[
                    PassportItemRead.model_validate(passport)
                    for passport in passports
                ],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, passport_patch: PassportPatch) -> PassportRead:
        async with self.uow as uow:
            passport_data = passport_patch.model_dump()
            result = PassportRead.model_validate(
                await self._update(passport_data.pop("id"), passport_data)
            )
            await uow.commit()
        return result

    async def put(self, passport_put: PassportPut) -> PassportRead:
        async with self.uow as uow:
            result = PassportRead.model_validate(
                await self._upsert(passport_put)
            )
            await uow.commit()
        return result

    async def delete(self, passport_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(passport_id)
            await uow.commit()

    async def check_ownership(
        self, passport_id: UUID, profile_id: UUID
    ) -> None:
        async with self.uow:
            await self._check_ownership(passport_id, profile_id)

    async def ensure_existance(self, passport_id: UUID) -> None:
        async with self.uow:
            await self._ensure_existance(passport_id)


class NameVariantService(BaseService[PassportUOW]):
    @required_transaction
    async def _create(self, name_variant: NameVariantPut) -> NameVariantORM:
        return await self.uow.name_variants.add_n_return(
            name_variant.model_dump()
        )

    @required_transaction
    async def _read(self, name_variant_id: UUID) -> NameVariantORM | None:
        name_variant = await self.uow.name_variants.get_by_id(name_variant_id)
        if name_variant is None:
            raise PassportNotExistsException()
        return name_variant

    @required_transaction
    async def _update(
        self,
        name_variant_id: UUID,
        name_variant_data: dict,
        *,
        flush: bool = False,
    ) -> NameVariantORM:
        name_variant = await self.uow.name_variants.update_one(
            name_variant_id, name_variant_data, flush
        )
        if name_variant is None:
            raise PassportNotExistsException()
        return name_variant

    @required_transaction
    async def _upsert(self, name_variant_put: NameVariantPut) -> NameVariantORM:
        return await self.uow.name_variants.upsert(
            name_variant_put.model_dump()
        )

    @required_transaction
    async def _delete(self, name_variant_id: UUID) -> None:
        await self.uow.name_variants.delete_one(name_variant_id)

    async def create(
        self, name_variant_create: NameVariantCreate, passport_id: UUID
    ) -> NameVariantRead:
        async with self.uow as uow:
            result = NameVariantRead.model_validate(
                await self._create(name_variant_create, passport_id)
            )
            await uow.commit()
        return result

    async def read(self, name_variant_id: UUID) -> NameVariantRead:
        async with self.uow:
            return NameVariantRead.model_validate(
                await self._read(name_variant_id)
            )

    async def patch(
        self, name_variant_patch: NameVariantPatch
    ) -> NameVariantRead:
        async with self.uow as uow:
            name_variant_data = name_variant_patch.model_dump()
            result = NameVariantRead.model_validate(
                await self._update(
                    name_variant_data.pop("id"), name_variant_data
                )
            )
            await uow.commit()
        return result

    async def put(self, name_variant_put: NameVariantPut) -> NameVariantRead:
        async with self.uow as uow:
            result = NameVariantRead.model_validate(
                await self._upsert(name_variant_put)
            )
            await uow.commit()
        return result

    async def delete(self, name_variant_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(name_variant_id)
            await uow.commit()
