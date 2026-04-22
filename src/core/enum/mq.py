from enum import StrEnum


from core.utils.enum.prefix import prefix


@prefix("mail/")
class EmailQueue(StrEnum):
    VERIFY = "verify"