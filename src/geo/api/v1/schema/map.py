from pydantic import BaseModel

from core.schema.v1.mixin.dto import FromDTOMixinV1
from core.schema.v1.pagination import PageV1
from geo.api.v1.schema.address import AddressRead
from geo.api.v1.schema.location import LocationRead


class MapResult(BaseModel, FromDTOMixinV1):
    """Two separate paginated lists rather than one merged/tagged
    collection -- simpler for a map layer to consume as two marker types
    (two icons), and each already paginates independently."""

    addresses: PageV1[AddressRead]
    locations: PageV1[LocationRead]
