from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from geo.dependency.address import AddressUOWDep
from geo.filter.address import AddressFilter
from geo.schema.address import (
    AddressCascadeCreate,
    AddressCreate,
    AddressPatch,
    AddressPatchData,
    AddressPut,
    AddressPutData,
    AddressRead,
)
from geo.schema.point import Point
from geo.service.address import AddressService

router = APIRouter(prefix="/addresses", tags=["address"])

logger = getLogger(__name__)

@router.get("", responses={**auth_responses()})
async def get_addresses(
    uow: AddressUOWDep,
    user: UserJWTDep,
    filter: AddressFilter = FilterDepends(AddressFilter),
    page_param=Depends(SPageParam),
    near_lat: float | None = None,
    near_lon: float | None = None,
) -> SPage[AddressRead]:
    # near_lat/near_lon sort by distance instead of name, but only when search is empty (see service)
    near = Point(lat=near_lat, lon=near_lon) if near_lat is not None and near_lon is not None else None
    return await AddressService(uow).search(filter, page_param, near=near)

@router.get("/{address_id}", responses={**auth_responses(), **entity_not_found_responses("address")})
async def get_address(
    address_id: UUID, user: UserJWTDep, uow: AddressUOWDep
) -> AddressRead:
    return await AddressService(uow).read(address_id)

@router.post("", responses={**auth_responses()})
async def create_address(
    address: AddressCreate,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).create(address)

@router.post("/cascade", responses={**auth_responses()})
async def create_address_cascade(
    address: AddressCascadeCreate,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    """Like ``POST /addresses``, but for a hand-entered address whose city
    isn't in the database yet -- names the country/region/city instead of
    requiring an existing ``city_id``, and creates whichever levels are
    missing."""
    return await AddressService(uow).create_cascade(address)

@router.put("/{address_id}", responses={**auth_responses(), **entity_not_found_responses("address")})
async def put_address(
    address_id: UUID,
    address: AddressPutData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).put(
        AddressPut(id=address_id, **address.model_dump())
    )

@router.patch("/{address_id}", responses={**auth_responses(), **entity_not_found_responses("address")})
async def patch_address(
    address_id: UUID,
    address: AddressPatchData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).patch(
        AddressPatch(id=address_id, **address.model_dump())
    )

@router.delete("/{address_id}", responses={**auth_responses(), **entity_not_found_responses("address")})
async def delete_address(
    address_id: UUID, user: SuperUserJWTDep, uow: AddressUOWDep
) -> None:
    await AddressService(uow).delete(address_id)