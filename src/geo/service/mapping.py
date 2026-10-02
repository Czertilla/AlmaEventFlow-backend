from geo.dto.address import AddressDTO
from geo.models.address import AddressORM
from geo.models.spot import point_from_geometry


def address_to_dto(address: AddressORM) -> AddressDTO:
    return AddressDTO(
        id=address.id,
        city_id=address.city_id,
        name=address.name,
        spot=point_from_geometry(address.spot),
        parsed=address.parsed,
        source=address.source,
    )
