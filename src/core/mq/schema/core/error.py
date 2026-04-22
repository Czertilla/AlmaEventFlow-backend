from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class MQError(BaseModel):
    id: UUID | None = Field(
        description="a unique error identifier for quick detection in logs",
        default_factory=uuid4,
    )
    code: int | None
    detail: str
    extra: dict[str, str | int | float | bool] = {}
