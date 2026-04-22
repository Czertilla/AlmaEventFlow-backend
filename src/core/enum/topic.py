from enum import StrEnum


class PersonTopic(StrEnum):
    CREATED = "person-created"
    UPDATED = "person-updated"
    DELETED = "person-deleted"


class OrganizationTopic(StrEnum):
    CREATED = "organization-created"
    UPDATED = "organization-updated"
    DELETED = "organization-deleted"


class AddressTopic(StrEnum):
    CREATED = "address-created"
    UPDATED = "address-updated"
    DELETED = "address-deleted"


class LocationTopic(StrEnum):
    CREATED = "location-created"
    UPDATED = "location-updated"
    DELETED = "location-deleted"


class CollectiveTopic(StrEnum):
    CREATED = "collective-created"
    UPDATED = "collective-updated"
    DELETED = "collective-deleted"
