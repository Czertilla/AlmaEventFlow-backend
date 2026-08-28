from profile.repository.passport import NameVariantRepo, PassportRepo

from core.uow.sqlalchemy import UnitOfWork


class PassportMixin:
    passports: PassportRepo
    name_variants: NameVariantRepo


class PassportUOW(UnitOfWork, PassportMixin): ...
