from enum import StrEnum


class AccessAction(StrEnum):
    READ = "read"
    EXPORT = "export"
    REQUEST_CREATED = "request_created"
    GRANT_APPROVED = "grant_approved"
    GRANT_DECLINED = "grant_declined"
    GRANT_REVOKED = "grant_revoked"
    KEY_DESTROYED = "key_destroyed"
    DENIED = "denied"


OUTCOME_OK = "ok"


class GrantStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    DECLINED = "declined"
    REVOKED = "revoked"


class GrantState(StrEnum):
    """What a subject or a grantee sees: the stored status, or `expired` once the
    request has run out."""

    PENDING = "pending"
    ACTIVE = "active"
    DECLINED = "declined"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SkipReason(StrEnum):
    PENDING = "pending"
    DECLINED = "declined"
    REVOKED = "revoked"
    EXPIRED = "expired"
    NOT_MEMBER = "not_member"
