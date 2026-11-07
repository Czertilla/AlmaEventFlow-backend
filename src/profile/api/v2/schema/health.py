from profile.crypto import Health

from pydantic import BaseModel


class KeyHealthRead(BaseModel):
    status: Health
