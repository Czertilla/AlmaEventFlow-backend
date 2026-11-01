from profile.repository.profile import ProfileRepo
from profile.uow.contact import ContactMixin
from profile.uow.passport import PassportMixin
from profile.uow.person import PersonMixin
from profile.uow.person_key import PersonalDataUOW

from core.uow.sqlalchemy import UnitOfWork


class ProfileMixin:
    profiles: ProfileRepo


class ProfileUOW(UnitOfWork, ProfileMixin): ...


class ProfilePassportUOW(PersonalDataUOW, ProfileMixin, PassportMixin): ...


class ProfileExtendedUOW(
    PersonalDataUOW, ProfileMixin, PersonMixin, ContactMixin, PassportMixin
): ...
