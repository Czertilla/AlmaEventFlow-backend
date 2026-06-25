from datetime import date
from uuid import uuid4

from core.enum.notify import NotificationCategory
from event.service.notification import _build_requests, is_trigger_status


def test_groups_persons_per_event_with_safe_payload():
    event_a, event_b = uuid4(), uuid4()
    p1, p2, p3 = uuid4(), uuid4(), uuid4()
    rows = [
        (event_a, "Concert", date(2026, 5, 1), p1),
        (event_a, "Concert", date(2026, 5, 1), p2),
        (event_b, "Rehearsal", None, p3),
    ]

    requests = _build_requests(rows)

    by_event = {req.data["event_id"]: req for req in requests}
    assert set(by_event) == {str(event_a), str(event_b)}

    req_a = by_event[str(event_a)]
    assert req_a.category is NotificationCategory.attendance
    assert set(req_a.person_ids) == {p1, p2}
    assert not req_a.user_ids
    assert req_a.action_url.endswith(f"/event/{event_a}")
    assert req_a.data["event_name"] == "Concert"
    assert req_a.data["event_date"] == "2026-05-01"

    req_b = by_event[str(event_b)]
    assert req_b.person_ids == [p3]
    assert "event_date" not in req_b.data


def test_payload_excludes_unsafe_fields():
    event_id = uuid4()
    rows = [(event_id, "Name", date(2026, 1, 1), uuid4())]
    request = _build_requests(rows)[0]
    assert set(request.data) <= {"event_id", "event_name", "event_date", "action_url"}


def test_is_trigger_status_default_active():
    assert is_trigger_status("active") is True
    assert is_trigger_status("draft") is False
    assert is_trigger_status(None) is False
