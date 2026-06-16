from enum import StrEnum


class EventStatusEnumV1(StrEnum):
    draft = "draft"
    template = "template"
    active = "active"
    archived = "archived"
