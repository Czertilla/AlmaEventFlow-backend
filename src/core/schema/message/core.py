from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID, uuid4

T = TypeVar("T", bound=BaseModel)


class MQError(BaseModel):
    err_id: UUID | None = Field(
        description="a unique error identifier for quick detection in logs",
        default_factory=uuid4,
    )
    code: int = 400
    detail: str
    extra: dict[str, str]


class MQResponse(BaseModel, Generic[T]):
    data: T | None
    error: MQError | None = Field(
        default=None,
        description="""In a normal situation, this field will remain empty, but in 
        exceptional cases it will store information about the error.""",
    )


class MQRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MQEvent(MQRequest, Generic[T]):
    event_id: UUID = Field(default_factory=uuid4)
    data: T
