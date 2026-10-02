from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from geo.api.v1.schema.address import (
    AddressCascadeCreate,
    AddressCreate,
    AddressPatch,
    AddressPatchData,
    AddressPut,
    AddressPutData,
    AddressRead,
)
from geo.api.v1.schema.point import Point
from geo.dependency.address import AddressUOWDep
from geo.filter.address import AddressFilter
from geo.service.address import AddressService

router = APIRouter(prefix="/addresses", tags=["address"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_addresses(
    uow: AddressUOWDep,
    user: UserJWTDep,
    filter: AddressFilter = FilterDepends(AddressFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
    near_lat: float | None = None,
    near_lon: float | None = None,
) -> PageV1[AddressRead]:
    # near_lat/near_lon sort by distance instead of name, but only when search is empty (see service)
    near = (
        Point(lat=near_lat, lon=near_lon).to_dto()
        if near_lat is not None and near_lon is not None
        else None
    )
    return PageV1[AddressRead].from_dto(
        await AddressService(uow).search(
            filter.to_dto(), page_param.to_dto(), near=near
        )
    )


@router.get(
    "/{address_id}",
    responses={**auth_responses(), **entity_not_found_responses("address")},
)
async def get_address(
    address_id: UUID, user: UserJWTDep, uow: AddressUOWDep
) -> AddressRead:
    return AddressRead.from_dto(await AddressService(uow).read(address_id))


@router.post("", responses={**auth_responses()})
async def create_address(
    address: AddressCreate,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return AddressRead.from_dto(await AddressService(uow).create(address.to_dto()))


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
    return AddressRead.from_dto(
        await AddressService(uow).create_cascade(address.to_dto())
    )


@router.put(
    "/{address_id}",
    responses={**auth_responses(), **entity_not_found_responses("address")},
)
async def put_address(
    address_id: UUID,
    address: AddressPutData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return AddressRead.from_dto(
        await AddressService(uow).put(
            AddressPut.model_validate(
                {"id": address_id, **address.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/{address_id}",
    responses={**auth_responses(), **entity_not_found_responses("address")},
)
async def patch_address(
    address_id: UUID,
    address: AddressPatchData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return AddressRead.from_dto(
        await AddressService(uow).patch(
            AddressPatch.model_validate(
                {"id": address_id, **address.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/{address_id}",
    responses={**auth_responses(), **entity_not_found_responses("address")},
)
async def delete_address(
    address_id: UUID, user: SuperUserJWTDep, uow: AddressUOWDep
) -> None:
    await AddressService(uow).delete(address_id)
