from collections.abc import Collection
from logging import getLogger
from profile.exc.event import EventUnavailableError
from uuid import UUID

from core.broker.rpc import rpc_call
from core.enum.rpc import EventRPC
from core.schema.message.event import (
    SharedCollectiveSubjectsRequest,
    SharedCollectiveSubjectsResponse,
)

logger = getLogger(__name__)

RPC_TIMEOUT_S = 2.0


async def shared_collective_subjects(
    viewer_person_id: UUID, subjects: Collection[UUID] | None = None
) -> set[UUID]:
    request = SharedCollectiveSubjectsRequest(
        viewer_person_id=viewer_person_id,
        subject_ids=None if subjects is None else list(subjects),
    )
    try:
        response = await rpc_call(
            EventRPC.SHARED_COLLECTIVE_SUBJECTS,
            request,
            SharedCollectiveSubjectsResponse,
            timeout_s=RPC_TIMEOUT_S,
        )
    except Exception as exc:
        logger.exception(
            "The event service did not answer %s", EventRPC.SHARED_COLLECTIVE_SUBJECTS
        )
        raise EventUnavailableError() from exc
    return set(response.person_ids)
