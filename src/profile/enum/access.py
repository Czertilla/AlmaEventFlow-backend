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
