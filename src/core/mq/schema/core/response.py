from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from .error import MQError


T = TypeVar("T", bound=BaseModel)


class MQResponse(BaseModel, Generic[T]):
    data: T | None
    error: MQError | None = Field(
        default=None,
        description="""In a normal situation, this field will remain empty, but in 
        exceptional cases it will store information about the error.""",
    )
