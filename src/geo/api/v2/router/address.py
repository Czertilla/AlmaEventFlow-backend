from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from geo.api.v2.schema.address import AddressReadV2
from geo.dependency.address import AddressUOWDep
from geo.service.address import AddressService

router = APIRouter(prefix="/addresses", tags=["address"])


@router.get(
    "/{address_id}",
    responses={**auth_responses(), **entity_not_found_responses("address")},
)
async def get_address(
    address_id: UUID, user: UserJWTDep, uow: AddressUOWDep
) -> AddressReadV2:
    return AddressReadV2.from_dto(await AddressService(uow).read(address_id))
