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


class AccountTopic(StrEnum):
    """User account events published by the ``user`` service and projected by
    ``notify`` into its local ``account`` read model."""

    CREATED = "account-created"
    UPDATED = "account-updated"
    EMAIL_VERIFIED = "account-email-verified"
    DELETED = "account-deleted"
