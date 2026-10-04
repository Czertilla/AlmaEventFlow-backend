from logging import getLogger
from profile.dto.passport import (
    NameVariantCreateDTO,
    NameVariantDTO,
    NameVariantPatchDTO,
    NameVariantPutDTO,
    PassportCreateDTO,
    PassportDTO,
    PassportFilterDTO,
    PassportPatchDTO,
    PassportPutDTO,
)
from profile.exc.passport import (
    NameVariantNotExistsException,
    PassportNotExistsException,
    PassportOwnershipException,
)
from profile.filter.passport import PassportFilter
from profile.models.passport import NameVariantORM, PassportORM
from profile.uow.passport import PassportUOW
from profile.uow.profile import ProfilePassportUOW
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict, dto_from_orm
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.service.base import BaseService, required_transaction

logger = getLogger(__name__)


class PassportService(BaseService[PassportUOW | ProfilePassportUOW]):
    @staticmethod
    def _to_dto(passport: PassportORM) -> PassportDTO:
        name_variant = passport.name_variant
        return PassportDTO(
            id=passport.id,
            profile_id=passport.profile_id,
            number=passport.number,
            expire_date=passport.expire_date,
            is_foreign=passport.is_foreign,
            issued_date=passport.issued_date,
            issued_authority=passport.issued_authority,
            name_variant=dto_from_orm(name_variant, NameVariantCreateDTO)
            if name_variant
            else None,
            created_at=passport.created_at,
            edited_at=passport.edited_at,
        )

    @required_transaction
    async def _create(self, passport_create: PassportCreateDTO) -> PassportORM:
        passport_data = dto_dict(passport_create, exclude={"name_variant"})
        name_variant = passport_create.name_variant

        passport = await self.uow.passports.add_n_return(data=passport_data)

        if name_variant:
            name_variant_data = dto_dict(name_variant)
            name_variant_data["id"] = passport.id
            await self.uow.name_variants.add_n_return(data=name_variant_data)

        return passport

    @required_transaction
    async def _check_ownership(self, passport_id: UUID, profile_id: UUID):
        exists = await self.uow.passports.get_by_id(passport_id)
        if exists and exists.profile_id != profile_id:
            raise PassportOwnershipException()

    @required_transaction
    async def _read(self, passport_id: UUID) -> PassportORM:
        passport = await self.uow.passports.get_by_id(passport_id)
        if passport is None:
            raise PassportNotExistsException()
        return passport

    @required_transaction
    async def _ensure_existance(self, passport_id: UUID):
        if not await self.uow.passports.exists_id(passport_id):
            raise PassportNotExistsException()

    @required_transaction
    async def _update(
        self,
        passport_id: UUID,
        passport_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> PassportORM:
        passport = await self.uow.passports.update_one(
            passport_id, passport_data, flush
        )
        if passport is None:
            raise PassportNotExistsException()
        return passport

    @required_transaction
    async def _upsert(self, passport_put: PassportPutDTO) -> PassportORM:
        await self._check_ownership(passport_put.id, passport_put.profile_id)
        passport = await self.uow.passports.upsert(
            dto_dict(passport_put, exclude={"name_variant"})
        )
        if passport is None:
            raise PassportNotExistsException()
        return passport

    @required_transaction
    async def _delete(self, passport_id: UUID) -> None:
        await self.uow.passports.delete_one(passport_id)

    async def create(self, passport_create: PassportCreateDTO) -> PassportDTO:
        async with self.uow as uow:
            created = await self._create(passport_create)
            result = self._to_dto(await self._read(created.id))
            await uow.commit()
        return result

    async def read(self, passport_id: UUID) -> PassportDTO:
        async with self.uow:
            return self._to_dto(await self._read(passport_id))

    async def search(
        self,
        filter: PassportFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[PassportDTO]:
        async with self.uow as uow:
            passports, total = await uow.passports.search(
                PassportFilter.from_dto(filter), page_params
            )
            return PageDTO(
                items=[self._to_dto(passport) for passport in passports],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def search_by_profile(
        self,
        profile_id: UUID,
        filter: PassportFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[PassportDTO]:
        async with self.uow as uow:
            passports, total = await uow.passports.search(
                PassportFilter.from_dto(filter),
                page_params,
                scope=[PassportORM.profile_id == profile_id],
            )
            return PageDTO(
                items=[self._to_dto(passport) for passport in passports],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def patch(self, passport_patch: PassportPatchDTO) -> PassportDTO:
        async with self.uow as uow:
            passport_data = dto_dict(passport_patch, only_set=True, exclude={"id"})
            updated = await self._update(passport_patch.id, passport_data)
            result = self._to_dto(await self._read(updated.id))
            await uow.commit()
        return result

    async def put(self, passport_put: PassportPutDTO) -> PassportDTO:
        async with self.uow as uow:
            upserted = await self._upsert(passport_put)
            result = self._to_dto(await self._read(upserted.id))
            await uow.commit()
        return result

    async def delete(self, passport_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(passport_id)
            await uow.commit()

    async def check_ownership(self, passport_id: UUID, profile_id: UUID) -> None:
        async with self.uow:
            await self._check_ownership(passport_id, profile_id)

    async def ensure_existance(self, passport_id: UUID) -> None:
        async with self.uow:
            await self._ensure_existance(passport_id)


class NameVariantService(BaseService[PassportUOW]):
    @staticmethod
    def _to_dto(name_variant: NameVariantORM) -> NameVariantDTO:
        return dto_from_orm(name_variant, NameVariantDTO)

    @required_transaction
    async def _read(self, name_variant_id: UUID) -> NameVariantORM:
        name_variant = await self.uow.name_variants.get_by_id(name_variant_id)
        if name_variant is None:
            raise NameVariantNotExistsException()
        return name_variant

    @required_transaction
    async def _update(
        self,
        name_variant_id: UUID,
        name_variant_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> NameVariantORM:
        name_variant = await self.uow.name_variants.update_one(
            name_variant_id, name_variant_data, flush
        )
        if name_variant is None:
            raise NameVariantNotExistsException()
        return name_variant

    @required_transaction
    async def _upsert(self, name_variant_put: NameVariantPutDTO) -> NameVariantORM:
        name_variant = await self.uow.name_variants.upsert(dto_dict(name_variant_put))
        if name_variant is None:
            raise NameVariantNotExistsException()
        return name_variant

    @required_transaction
    async def _delete(self, name_variant_id: UUID) -> None:
        await self.uow.name_variants.delete_one(name_variant_id)

    async def read(self, name_variant_id: UUID) -> NameVariantDTO:
        async with self.uow:
            return self._to_dto(await self._read(name_variant_id))

    async def patch(self, name_variant_patch: NameVariantPatchDTO) -> NameVariantDTO:
        async with self.uow as uow:
            name_variant_data = dto_dict(
                name_variant_patch, only_set=True, exclude={"id"}
            )
            result = self._to_dto(
                await self._update(name_variant_patch.id, name_variant_data)
            )
            await uow.commit()
        return result

    async def put(self, name_variant_put: NameVariantPutDTO) -> NameVariantDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._upsert(name_variant_put))
            await uow.commit()
        return result

    async def delete(self, name_variant_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(name_variant_id)
            await uow.commit()
