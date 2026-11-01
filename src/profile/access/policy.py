from collections.abc import Collection
from logging import getLogger
from profile.access.data import AccessData
from profile.access.decision import Decision, Via
from profile.enum.audience import Audience, clamp
from profile.exc.event import EventUnavailableError
from profile.registry import PersonalField, get_field
from uuid import UUID

from core.schema.user import UserJWT
from core.utils.exc.http import VancedHTTPException

logger = getLogger(__name__)


class PersonalDataPolicy:
    """The one place that decides who may see which personal field of whom.

    The viewer sees their own data; a superuser sees everything; anyone else sees
    what the owner's audience for the field lets them. The audience is the stored
    setting, else the field's default (wider for the head of a university or a
    faculty), kept within the field's own range.
    """

    def __init__(
        self, viewer: UserJWT, viewer_person_id: UUID | None, data: AccessData
    ) -> None:
        self.viewer = viewer
        self.viewer_person_id = viewer_person_id
        self.data = data

    @property
    def unrestricted(self) -> bool:
        return self.viewer.is_superuser

    def ensure_owner(self, subject_id: UUID, hidden: VancedHTTPException) -> None:
        if not self.unrestricted and self.viewer_person_id != subject_id:
            raise hidden

    async def can_view(self, subject_id: UUID, field_key: str) -> Decision:
        return (await self.decide([subject_id], field_key))[subject_id]

    async def decide(
        self, subject_ids: Collection[UUID], field_key: str
    ) -> dict[UUID, Decision]:
        field = get_field(field_key)
        decisions: dict[UUID, Decision] = {}
        pending: set[UUID] = set()
        for subject_id in dict.fromkeys(subject_ids):
            if self.unrestricted:
                decisions[subject_id] = Decision.granted(Via.SUPERUSER)
            elif subject_id == self.viewer_person_id:
                decisions[subject_id] = Decision.granted(Via.SELF)
            else:
                pending.add(subject_id)
        if not pending:
            return decisions
        audiences = await self._audiences(field, pending)
        context = {
            s for s, audience in audiences.items() if audience == Audience.CONTEXT
        }
        shared, available = await self._shared(context)
        for subject_id in pending:
            decisions[subject_id] = self._by_audience(
                audiences[subject_id], subject_id in shared, available
            )
        return decisions

    async def visible_subjects(self, field_key: str) -> set[UUID] | None:
        """The subjects whose field the viewer may see; `None` when no one is
        hidden from them."""
        if self.unrestricted:
            return None
        field = get_field(field_key)
        visible: set[UUID] = (
            {self.viewer_person_id} if self.viewer_person_id is not None else set()
        )
        if field.deprecated:
            return visible
        if field.default_for(unit_head=False) == Audience.ALL_USERS:
            raise NotImplementedError("a field open to everyone by default has no list")
        stored = await self.data.stored_audiences(field.key, None)
        heads = await self._heads(field, None)
        shared: set[UUID] = set()
        if self.viewer_person_id is not None:
            shared, _ = await self._shared(None)
        for subject_id in {*stored, *heads, *shared}:
            audience = self._audience(field, stored, subject_id, subject_id in heads)
            if audience == Audience.ALL_USERS or (
                audience == Audience.CONTEXT and subject_id in shared
            ):
                visible.add(subject_id)
        return visible

    async def _audiences(
        self, field: PersonalField, subject_ids: Collection[UUID]
    ) -> dict[UUID, Audience]:
        if field.deprecated:
            return dict.fromkeys(subject_ids, Audience.PRIVATE)
        stored = await self.data.stored_audiences(field.key, subject_ids)
        heads = await self._heads(field, subject_ids)
        return {
            subject_id: self._audience(field, stored, subject_id, subject_id in heads)
            for subject_id in subject_ids
        }

    async def _heads(
        self, field: PersonalField, among: Collection[UUID] | None
    ) -> set[UUID]:
        if field.audience_default_for_unit_head is None:
            return set()
        return await self.data.unit_heads(among)

    @staticmethod
    def _audience(
        field: PersonalField,
        stored: dict[UUID, Audience],
        subject_id: UUID,
        unit_head: bool,
    ) -> Audience:
        chosen = stored.get(subject_id) or field.default_for(unit_head=unit_head)
        return clamp(chosen, field.audience_min, field.audience_max)

    async def _shared(
        self, subject_ids: Collection[UUID] | None
    ) -> tuple[set[UUID], bool]:
        if subject_ids is not None and not subject_ids:
            return set(), True
        if self.viewer_person_id is None:
            return set(), True
        try:
            return (
                await self.data.shared_subjects(self.viewer_person_id, subject_ids),
                True,
            )
        except EventUnavailableError:
            logger.warning("Shared collectives unknown, context is refused")
            return set(), False

    def _by_audience(
        self, audience: Audience, shares_collective: bool, event_available: bool
    ) -> Decision:
        match audience:
            case Audience.ALL_USERS:
                if self.viewer.is_active and self.viewer.is_verified:
                    return Decision.granted(Via.AUDIENCE)
                return Decision.refused("VIEWER_NOT_VERIFIED")
            case Audience.CONTEXT:
                if shares_collective:
                    return Decision.granted(Via.AUDIENCE)
                return Decision.refused(
                    "NO_SHARED_COLLECTIVE" if event_available else "CONTEXT_UNAVAILABLE"
                )
            case Audience.PRIVATE:
                return Decision.refused("PRIVATE")
