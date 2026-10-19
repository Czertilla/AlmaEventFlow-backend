from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from geo.api.v2.schema.location import LocationCreateV2, LocationReadV2
from geo.dependency.location import LocationUOWDep
from geo.service.location import LocationService

router = APIRouter(prefix="/locations", tags=["location"])


@router.get("", responses={**auth_responses()})
async def get_locations(
    ids: Annotated[
        list[UUID],
        Query(
            alias="id",
            min_length=1,
            max_length=50,
            description="Ids of the locations to read; repeat the parameter.",
        ),
    ],
    user: UserJWTDep,
    uow: LocationUOWDep,
) -> list[LocationReadV2]:
    """The locations with these ids, in the order given. An id nobody has
    is left out, so a list of remembered places never fails on a deleted one."""
    return [
        LocationReadV2.from_dto(location)
        for location in await LocationService(uow).read_many(ids)
    ]


@router.get(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def get_location(
    location_id: UUID, user: UserJWTDep, uow: LocationUOWDep
) -> LocationReadV2:
    return LocationReadV2.from_dto(await LocationService(uow).read(location_id))


@router.post("", responses={**auth_responses()})
async def create_location(
    location: LocationCreateV2, user: UserJWTDep, uow: LocationUOWDep
) -> LocationReadV2:
    """Same as the v1 create, plus a `name` alone: a location that is only an
    address written as text, for when nothing about the place is on the map.
    Posting the same name again returns the location that exists."""
    return LocationReadV2.from_dto(await LocationService(uow).create(location.to_dto()))
