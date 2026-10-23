from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from event.api.v2.schema.event_page import EventPageRead
from event.dependency.view import ViewUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.event_page import EventPageService

router = APIRouter(prefix="/events", tags=["event"])


@router.get(
    "/{event_id}",
    responses={**auth_responses(), **entity_not_found_responses("event")},
)
async def get_event_page(
    event_id: UUID, user: UserJWTDep, uow: ViewUOWDep
) -> EventPageRead:
    """The event with its stages, its place and every participation, in one answer.
    The places of a collective come with the names of the members and their roles
    for its leader and its members only. An event the caller may not see is not
    found."""
    viewer = ProfileViewerDTO(person_id=user.person_id, is_superuser=user.is_superuser)
    return EventPageRead.from_dto(await EventPageService(uow).read(event_id, viewer))
