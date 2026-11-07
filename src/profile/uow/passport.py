from profile.repository.passport import NameVariantRepo, PassportRepo
from profile.uow.person_key import PersonalDataUOW


class PassportMixin:
    passports: PassportRepo
    name_variants: NameVariantRepo


class PassportUOW(PersonalDataUOW, PassportMixin): ...
