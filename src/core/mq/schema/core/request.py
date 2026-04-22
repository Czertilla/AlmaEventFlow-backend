from pydantic import BaseModel, ConfigDict


class MQRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
