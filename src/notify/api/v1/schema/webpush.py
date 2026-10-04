from pydantic import BaseModel


class VapidPublicKey(BaseModel):
    public_key: str
