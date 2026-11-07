from collections.abc import Collection
from dataclasses import replace
from profile.access import Decision, PersonalDataPolicy, Via
from profile.enum.audience import Audience
from profile.exc.event import EventUnavailableError
from profile.exc.profile import ProfileNotExistsException
from profile.registry import PERSON_FULLNAME, PersonalField, get_field
from uuid import UUID, uuid4

import pytest

from core.schema.user import UserJWT

FULLNAME = PERSON_FULLNAME
BIRTHDATE = "profile.birthdate"
DIET = "profile.diet"
PASSPORT = "passport.number"


class FakeData:
    def __init__(self) -> None:
        self.heads: set[UUID] = set()
        self.stored: dict[tuple[UUID, str], Audience] = {}
        self.shared: dict[UUID, set[UUID]] = {}
        self.down = False
        self.shared_calls = 0
        self.head_calls = 0

    async def unit_heads(self, among: Collection[UUID] | None) -> set[UUID]:
        self.head_calls += 1
        return self.heads if among is None else self.heads & set(among)

    async def stored_audiences(
        self, field_key: str, among: Collection[UUID] | None
    ) -> dict[UUID, Audience]:
        return {
            person: audience
            for (person, key), audience in self.stored.items()
            if key == field_key and (among is None or person in among)
        }

    async def shared_subjects(
        self, viewer_person_id: UUID, among: Collection[UUID] | None
    ) -> set[UUID]:
        self.shared_calls += 1
        if self.down:
            raise EventUnavailableError
        shared = self.shared.get(viewer_person_id, set())
        return set(shared) if among is None else shared & set(among)


def _viewer(
    *, person: UUID | None, superuser: bool = False, verified: bool = True
) -> UserJWT:
    return UserJWT(
        id=uuid4(),
        person_id=person,
        is_active=True,
        is_verified=verified,
        is_superuser=superuser,
    )


def _policy(
    data: FakeData,
    person: UUID | None,
    *,
    superuser: bool = False,
    verified: bool = True,
) -> PersonalDataPolicy:
    return PersonalDataPolicy(
        _viewer(person=person, superuser=superuser, verified=verified), person, data
    )


async def test_a_person_sees_their_own_fields() -> None:
    me = uuid4()

    decision = await _policy(FakeData(), me).can_view(me, PASSPORT)

    assert decision == Decision(True, Via.SELF)


async def test_a_superuser_sees_everything() -> None:
    decision = await _policy(FakeData(), uuid4(), superuser=True).can_view(
        uuid4(), PASSPORT
    )

    assert decision == Decision(True, Via.SUPERUSER)


async def test_a_private_field_is_refused_to_everyone_else() -> None:
    subject = uuid4()

    decision = await _policy(FakeData(), uuid4()).can_view(subject, BIRTHDATE)

    assert decision == Decision(False, Via.NONE, "PRIVATE")


async def test_a_sensitive_field_stays_private_whatever_is_stored() -> None:
    subject = uuid4()
    data = FakeData()
    data.stored[(subject, PASSPORT)] = Audience.ALL_USERS

    decision = await _policy(data, uuid4()).can_view(subject, PASSPORT)

    assert decision.allow is False


async def test_the_context_audience_needs_a_shared_collective() -> None:
    viewer, colleague, stranger = uuid4(), uuid4(), uuid4()
    data = FakeData()
    data.shared[viewer] = {colleague}

    decisions = await _policy(data, viewer).decide([colleague, stranger], FULLNAME)

    assert decisions[colleague] == Decision(True, Via.AUDIENCE)
    assert decisions[stranger] == Decision(False, Via.NONE, "NO_SHARED_COLLECTIVE")


async def test_the_open_audience_needs_a_verified_viewer() -> None:
    subject, viewer = uuid4(), uuid4()
    data = FakeData()
    data.stored[(subject, BIRTHDATE)] = Audience.ALL_USERS

    verified = await _policy(data, viewer).can_view(subject, BIRTHDATE)
    unverified = await _policy(data, viewer, verified=False).can_view(
        subject, BIRTHDATE
    )

    assert verified == Decision(True, Via.AUDIENCE)
    assert unverified == Decision(False, Via.NONE, "VIEWER_NOT_VERIFIED")


async def test_a_viewer_without_a_person_sees_only_the_open_audience() -> None:
    subject = uuid4()
    data = FakeData()
    data.stored[(subject, BIRTHDATE)] = Audience.ALL_USERS

    open_field = await _policy(data, None).can_view(subject, BIRTHDATE)
    context_field = await _policy(data, None).can_view(subject, FULLNAME)

    assert open_field.allow is True
    assert context_field.allow is False
    assert data.shared_calls == 0


async def test_the_head_of_a_unit_is_open_to_all_users_by_default() -> None:
    head, viewer = uuid4(), uuid4()
    data = FakeData()
    data.heads = {head}

    decision = await _policy(data, viewer).can_view(head, FULLNAME)

    assert decision == Decision(True, Via.AUDIENCE)
    assert data.shared_calls == 0


async def test_a_head_may_narrow_the_full_name_to_the_context() -> None:
    head, viewer = uuid4(), uuid4()
    data = FakeData()
    data.heads = {head}
    data.stored[(head, FULLNAME)] = Audience.CONTEXT

    decision = await _policy(data, viewer).can_view(head, FULLNAME)

    assert decision.allow is False


async def test_a_stored_audience_is_kept_within_the_range_of_the_field() -> None:
    subject, viewer = uuid4(), uuid4()
    data = FakeData()
    data.stored[(subject, FULLNAME)] = Audience.PRIVATE
    data.stored[(subject, DIET)] = Audience.ALL_USERS
    data.shared[viewer] = {subject}

    full_name = await _policy(data, viewer).can_view(subject, FULLNAME)
    diet = await _policy(data, viewer).can_view(subject, DIET)

    assert full_name.allow is True
    assert diet.allow is True
    assert (await _policy(data, uuid4()).can_view(subject, DIET)).allow is False


async def test_a_silent_event_refuses_the_context_but_not_the_open_audience() -> None:
    viewer, colleague, head = uuid4(), uuid4(), uuid4()
    data = FakeData()
    data.shared[viewer] = {colleague}
    data.heads = {head}
    data.down = True

    decisions = await _policy(data, viewer).decide([colleague, head], FULLNAME)

    assert decisions[colleague] == Decision(False, Via.NONE, "CONTEXT_UNAVAILABLE")
    assert decisions[head] == Decision(True, Via.AUDIENCE)


async def test_many_subjects_cost_one_question_to_event_and_one_to_the_heads() -> None:
    viewer = uuid4()
    subjects = [uuid4() for _ in range(40)]
    data = FakeData()
    data.shared[viewer] = set(subjects[:10])

    decisions = await _policy(data, viewer).decide(subjects, FULLNAME)

    assert sum(d.allow for d in decisions.values()) == 10
    assert data.shared_calls == 1
    assert data.head_calls == 1


async def test_the_viewers_own_ids_and_duplicates_are_not_asked_about() -> None:
    viewer, other = uuid4(), uuid4()
    data = FakeData()

    decisions = await _policy(data, viewer).decide([viewer, other, other], FULLNAME)

    assert list(decisions) == [viewer, other]
    assert data.shared_calls == 1


async def test_nobody_is_asked_about_when_only_the_viewer_remains() -> None:
    viewer = uuid4()
    data = FakeData()

    await _policy(data, viewer).decide([viewer], FULLNAME)

    assert data.shared_calls == 0
    assert data.head_calls == 0


async def test_a_deprecated_field_is_private(monkeypatch: pytest.MonkeyPatch) -> None:
    subject, viewer = uuid4(), uuid4()
    data = FakeData()
    data.stored[(subject, FULLNAME)] = Audience.ALL_USERS
    old = replace(get_field(FULLNAME), deprecated=True)

    def fake_get_field(_key: str) -> PersonalField:
        return old

    monkeypatch.setattr("profile.access.policy.get_field", fake_get_field)

    decision = await _policy(data, viewer).can_view(subject, FULLNAME)

    assert decision == Decision(False, Via.NONE, "PRIVATE")


async def test_visible_subjects_are_the_viewer_the_heads_and_the_shared() -> None:
    viewer, colleague, head, stranger = uuid4(), uuid4(), uuid4(), uuid4()
    data = FakeData()
    data.shared[viewer] = {colleague}
    data.heads = {head}

    visible = await _policy(data, viewer).visible_subjects(FULLNAME)

    assert visible == {viewer, colleague, head}
    assert visible is not None
    assert stranger not in visible


async def test_visible_subjects_follow_what_the_owners_stored() -> None:
    viewer, narrow_head, opener = uuid4(), uuid4(), uuid4()
    data = FakeData()
    data.heads = {narrow_head}
    data.stored[(narrow_head, FULLNAME)] = Audience.CONTEXT
    data.stored[(opener, FULLNAME)] = Audience.ALL_USERS

    visible = await _policy(data, viewer).visible_subjects(FULLNAME)

    assert visible == {viewer, opener}


async def test_visible_subjects_are_not_limited_for_a_superuser() -> None:
    policy = _policy(FakeData(), uuid4(), superuser=True)

    assert await policy.visible_subjects(FULLNAME) is None


async def test_visible_subjects_while_event_is_silent_are_the_open_audience() -> None:
    viewer, colleague, head = uuid4(), uuid4(), uuid4()
    data = FakeData()
    data.shared[viewer] = {colleague}
    data.heads = {head}
    data.down = True

    visible = await _policy(data, viewer).visible_subjects(FULLNAME)

    assert visible == {viewer, head}


async def test_the_owner_check_lets_the_owner_and_a_superuser_through() -> None:
    me, other = uuid4(), uuid4()

    _policy(FakeData(), me).ensure_owner(me, ProfileNotExistsException())
    _policy(FakeData(), other, superuser=True).ensure_owner(
        me, ProfileNotExistsException()
    )
    with pytest.raises(ProfileNotExistsException):
        _policy(FakeData(), other).ensure_owner(me, ProfileNotExistsException())
