from dataclasses import dataclass

from core.dto.pagination import PageDTO
from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO


@dataclass(frozen=True, slots=True)
class MapResultDTO:
    addresses: PageDTO[AddressDTO]
    locations: PageDTO[LocationDTO]
