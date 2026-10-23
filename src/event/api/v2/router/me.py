from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from event.api.v2.schema.feed import ViewerContext
from event.dependency.view import ViewUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.feed import FeedService

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/context", responses={**auth_responses()})
async def get_my_context(user: UserJWTDep, uow: ViewUOWDep) -> ViewerContext:
    """The collectives the caller leads or is a member of, with their names and
    the caller's membership in each: the whole picture a client needs at start."""
    viewer = ProfileViewerDTO(person_id=user.person_id, is_superuser=user.is_superuser)
    return ViewerContext.from_dto(await FeedService(uow).context(viewer))
