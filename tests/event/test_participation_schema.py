import datetime
from uuid import uuid4

import pytest

from event.api.v1.schema.me import MeParticipationCreate
from event.api.v1.schema.participation import (
    ParticipationCreate,
    ParticipationPatch,
    ParticipationPatchData,
    ParticipationPut,
    ParticipationPutData,
    ParticipationRead,
)
from event.dto.participation import ParticipationDTO
from event.enum.priority import EventPriorityEnumV1


@pytest.mark.parametrize("key", ["priority_degree", "EventPriorityEnumV1"])
def test_priority_is_accepted_under_its_name_and_the_legacy_key(key: str):
    create = ParticipationCreate.model_validate(
        {"event_id": uuid4(), "collective_id": uuid4(), key: "low"}
    )

    assert create.priority_degree == EventPriorityEnumV1.low


def test_me_participation_accepts_the_legacy_priority_key():
    create = MeParticipationCreate.model_validate(
        {"event_id": uuid4(), "EventPriorityEnumV1": "medium"}
    )

    assert create.to_dto().priority_degree == EventPriorityEnumV1.medium


def test_response_exposes_the_priority_as_priority_degree():
    dto = ParticipationDTO(
        id=uuid4(),
        event_id=uuid4(),
        collective_id=uuid4(),
        priority_degree=EventPriorityEnumV1.hight,
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        edited_at=None,
    )

    dumped = ParticipationRead.from_dto(dto).model_dump(mode="json")

    assert dumped["priority_degree"] == "hight"
    assert "EventPriorityEnumV1" not in dumped


def test_put_keeps_the_priority_from_the_request_body():
    body = ParticipationPutData(
        event_id=uuid4(), priority_degree=EventPriorityEnumV1.low
    )

    dto = ParticipationPut.model_validate({"id": uuid4(), **body.model_dump()}).to_dto()

    assert dto.priority_degree == EventPriorityEnumV1.low


def test_patch_tracks_an_explicit_null_priority():
    body = ParticipationPatchData.model_validate({"priority_degree": None})

    dto = ParticipationPatch.model_validate(
        {"id": uuid4(), **body.model_dump()}
    ).to_dto()

    assert "priority_degree" in dto.fields_set
    assert dto.priority_degree is None
