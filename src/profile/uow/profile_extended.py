from profile.repository.profile import ProfileRepo
from profile.uow.contact import ContactMixin
from profile.uow.passport import PassportMixin
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class ProfileExtendedMixin:
    profiles: ProfileRepo


class ProfileExtendedUOW(UnitOfWork, ProfileExtendedMixin, PersonMixin, ContactMixin, PassportMixin): ...