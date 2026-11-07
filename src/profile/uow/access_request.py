from profile.repository.access_request import AccessGrantRepo, AccessRequestRepo
from profile.uow.account import AccountMixin
from profile.uow.person_key import PersonalDataUOW


class AccessRequestMixin:
    access_requests: AccessRequestRepo
    access_grants: AccessGrantRepo


class AccessRequestUOW(PersonalDataUOW, AccessRequestMixin, AccountMixin): ...
