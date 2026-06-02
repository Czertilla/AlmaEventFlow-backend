from enum import StrEnum


class EventStatus(StrEnum):
    draft = "draft"
    template = "template"
    active = "active"
    archived = "archived"
