from enum import StrEnum
from core.utils.enum.prefix import prefix


@prefix("person/")
class PersonTopic(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"