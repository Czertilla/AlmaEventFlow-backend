from typing import Literal

from pydantic import BaseModel


class HealthV1(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
