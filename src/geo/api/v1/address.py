from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from geo.dependency.address import AddressUOWDep
from geo.schema.address import (
    AddressCreate,
    AddressPatch,
    AddressPatchData,
    AddressPut,
    AddressPutData,
    AddressRead,
)
from geo.service.address import AddressService

router = APIRouter(prefix="/addresses", tags=["address"])

logger = getLogger(__name__)

@router.get("/{address_id}")
async def get_address(
    address_id: int, user: UserJWTDep, uow: AddressUOWDep
) -> AddressRead:
    return await AddressService(uow).read(address_id)

@router.post("/new")
async def create_address(
    address: AddressCreate,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).create(address)

@router.put("/{address_id}")
async def put_address(
    address_id: int,
    address: AddressPutData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).put(
        AddressPut(id=address_id, **address.model_dump())
    )

@router.patch("/{address_id}")
async def patch_address(
    address_id: int,
    address: AddressPatchData,
    user: SuperUserJWTDep,
    uow: AddressUOWDep,
) -> AddressRead:
    return await AddressService(uow).patch(
        AddressPatch(id=address_id, **address.model_dump())
    )

@router.delete("/{address_id}")
async def delete_address(
    address_id: int, user: SuperUserJWTDep, uow: AddressUOWDep
) -> None:
    await AddressService(uow).delete(address_id)