from profile.uow.account import AccountMixin
from profile.uow.contact import ContactMixin
from profile.uow.diet import DietMixin
from profile.uow.organization import OrganizationMixin
from profile.uow.person_key import PersonalDataUOW
from profile.uow.profile import ProfileMixin
from profile.uow.student import StudentMixin


class MyProfileUOW(
    PersonalDataUOW,
    AccountMixin,
    ProfileMixin,
    StudentMixin,
    ContactMixin,
    DietMixin,
    OrganizationMixin,
): ...
