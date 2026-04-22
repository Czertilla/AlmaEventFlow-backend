from uuid import UUID, uuid4

from pydantic import Field


class UUIDMixin:
    id: UUID = Field(default_factory=uuid4)
