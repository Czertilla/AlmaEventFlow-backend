from profile.uow.account import AccountMixin
from profile.uow.contact import ContactMixin
from profile.uow.diet import DietMixin
from profile.uow.organization import OrganizationMixin
from profile.uow.person import PersonMixin
from profile.uow.profile import ProfileMixin
from profile.uow.student import StudentMixin

from core.uow.sqlalchemy import UnitOfWork


class MyProfileUOW(
    UnitOfWork,
    AccountMixin,
    PersonMixin,
    ProfileMixin,
    StudentMixin,
    ContactMixin,
    DietMixin,
    OrganizationMixin,
): ...
