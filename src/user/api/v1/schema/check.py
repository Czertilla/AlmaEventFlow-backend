from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CheckResponse(BaseModel):
    username: Annotated[str, Field(max_length=50)]
    exists: bool

    model_config = ConfigDict(from_attributes=True)
