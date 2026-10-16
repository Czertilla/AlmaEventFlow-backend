from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO
from geo.models.address import AddressORM
from geo.models.location import LocationORM
from geo.models.spot import point_from_geometry


def address_to_dto(address: AddressORM) -> AddressDTO:
    return AddressDTO(
        id=address.id,
        city_id=address.city_id,
        name=address.name,
        spot=point_from_geometry(address.spot),
        parsed=address.parsed,
        source=address.source,
        created_at=address.created_at,
        edited_at=address.edited_at,
        locality=address.locality,
    )


def location_to_dto(location: LocationORM) -> LocationDTO:
    address = location.address
    return LocationDTO(
        id=location.id,
        name=location.name,
        address_id=location.address_id,
        spot=point_from_geometry(location.spot),
        address=address_to_dto(address) if address else None,
        created_at=location.created_at,
        edited_at=location.edited_at,
    )

