from pydantic import BaseModel


class SError(BaseModel):
    detail: str
    status_code: int
