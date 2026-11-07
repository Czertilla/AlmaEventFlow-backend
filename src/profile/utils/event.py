from collections.abc import Collection
from logging import getLogger
from profile.dto.access_request import CollectiveLeadDTO
from profile.exc.event import EventUnavailableError
from uuid import UUID

from core.broker.rpc import rpc_call
from core.enum.rpc import EventRPC
from core.schema.message.event import (
    CollectiveActiveMembersRequest,
    CollectiveActiveMembersResponse,
    CollectivePrincipalCheckRequest,
    CollectivePrincipalCheckResponse,
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


async def collective_principal(
    person_id: UUID, collective_id: UUID
) -> CollectiveLeadDTO:
    """Whether the person leads the collective now; no retry, no cache."""
    try:
        response = await rpc_call(
            EventRPC.COLLECTIVE_PRINCIPAL_CHECK,
            CollectivePrincipalCheckRequest(
                person_id=person_id, collective_id=collective_id
            ),
            CollectivePrincipalCheckResponse,
            timeout_s=RPC_TIMEOUT_S,
        )
    except Exception as exc:
        logger.exception(
            "The event service did not answer %s", EventRPC.COLLECTIVE_PRINCIPAL_CHECK
        )
        raise EventUnavailableError() from exc
    return CollectiveLeadDTO(
        is_principal=response.is_principal,
        name=response.name,
        is_verified=response.is_verified,
    )


async def collective_active_members(collective_id: UUID) -> set[UUID]:
    """The active members of the collective now; no retry, no cache."""
    try:
        response = await rpc_call(
            EventRPC.COLLECTIVE_ACTIVE_MEMBERS,
            CollectiveActiveMembersRequest(collective_id=collective_id),
            CollectiveActiveMembersResponse,
            timeout_s=RPC_TIMEOUT_S,
        )
    except Exception as exc:
        logger.exception(
            "The event service did not answer %s", EventRPC.COLLECTIVE_ACTIVE_MEMBERS
        )
        raise EventUnavailableError() from exc
    return set(response.person_ids)
