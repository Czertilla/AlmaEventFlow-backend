from datetime import datetime
from uuid import uuid4

from event.api.v1.schema.event import EventPatch, EventPatchData
from event.api.v1.schema.stage import StageCreateData
from event.dto.stage import StageCreateDataDTO
from event.filter.event import EventFilter


def test_patch_to_dto_tracks_only_explicitly_sent_fields():
    event_id = uuid4()
    patch_data = EventPatchData(name="Renamed")
    patch = EventPatch.model_validate(
        {"id": event_id, **patch_data.model_dump()}
    )

    dto = patch.to_dto()

    assert dto.fields_set == {"id", "name"}
    assert dto.name == "Renamed"
    assert dto.date is None
    assert "date" not in dto.fields_set


def test_patch_to_dto_tracks_an_explicit_null_as_set():
    event_id = uuid4()
    patch_data = EventPatchData(location_id=None)
    patch = EventPatch.model_validate(
        {"id": event_id, **patch_data.model_dump()}
    )

    dto = patch.to_dto()

    assert "location_id" in dto.fields_set
    assert dto.location_id is None
    assert "name" not in dto.fields_set


def test_event_filter_dto_round_trip_preserves_query_fields():
    filter_ = EventFilter(search="concert")
    filter_.participant_id = uuid4()

    dto = filter_.to_dto()
    rebuilt = EventFilter.from_dto(dto)

    assert rebuilt.search == "concert"
    assert rebuilt.participant_id == filter_.participant_id
    assert rebuilt.order_by == ["date"]


def test_stage_create_data_converts_to_its_own_dto_without_event_id():
    dto = StageCreateData(name="Opening", start_at=datetime(2026, 1, 1, 10)).to_dto()

    assert isinstance(dto, StageCreateDataDTO)
    assert dto.name == "Opening"
