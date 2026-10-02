from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class FromAttributesV1:
    """
    A mixin that allows the model to be initialized from attributes.
    """

    model_config = ConfigDict(from_attributes=True)


class PatchModelV1(BaseModel):
    """
    A model that forces exclude None values from the model dump.

    NOTE: Use instead BaseModel if you want to exclude None values from the
    model dump.

    Example:
    ```
    class MyModel(PatchModelV1):
        name: str
        age: int | None = None
    ```
    """

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return super().model_dump(exclude_unset=True, **kwargs)


class UUIDMixinV1:
    id: UUID

class PutUUIDMixinV1:
    id: UUID = Field(default_factory=uuid4)


class IDMixinV1:
    id: int


class TimestampMixinV1:
    created_at: datetime
    edited_at: datetime | None
