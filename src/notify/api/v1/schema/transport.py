from pydantic import BaseModel

from core.enum.notify import TransportTypeEnum


class TransportInfo(BaseModel):
    """Transport metadata for rendering the control panel."""

    type: TransportTypeEnum
    label: str
    requires_client: bool
    delegated: bool
    available: bool
