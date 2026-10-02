from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MQError(BaseModel):
    err_id: UUID | None = Field(
        description="a unique error identifier for quick detection in logs",
        default_factory=uuid4,
    )
    code: int = 400
    detail: str
    extra: dict[str, str]


class MQResponse[T: BaseModel](BaseModel):
    data: T | None
    error: MQError | None = Field(
        default=None,
        description="""In a normal situation, this field will remain empty, but in 
        exceptional cases it will store information about the error.""",
    )


class MQRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class MQEvent[T: BaseModel](MQRequest):
    event_id: UUID = Field(default_factory=uuid4)
    data: list[T]


class Ack(BaseModel):
    """No-payload success marker for RPC responses that have nothing to return."""

    ok: bool = True
