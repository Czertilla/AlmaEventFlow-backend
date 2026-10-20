from enum import StrEnum


class PersonLinkSource(StrEnum):
    OWN_PROFILE = "own_profile"
    INVITE = "invite"
    ADMIN = "admin"
    PERSON_DELETED = "person_deleted"
    BOOTSTRAP = "bootstrap"
