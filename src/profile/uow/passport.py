from core.uow.sqlalchemy import UnitOfWork
from profile.repository.passport import NameVariantRepo, PassportRepo


class PassportMixin:
    passports: PassportRepo
    name_variants: NameVariantRepo


class PassportUOW(UnitOfWork, PassportMixin): ...
