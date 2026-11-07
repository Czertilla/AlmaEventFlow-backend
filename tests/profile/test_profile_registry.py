import inspect
import json
from dataclasses import replace
from pathlib import Path
from profile.enum.audience import Audience
from profile.models import PersonORM
from profile.registry import FIELDS, Column, PersonalField, get_field
from profile.registry.validate import problems

import pytest
from pydantic import BaseModel

import core.schema.message.profile as profile_messages
from core.schema.message.core import MQEvent

RELEASED = json.loads(
    (Path(__file__).parent / "registry_released.json").read_text(encoding="utf-8")
)
METADATA = PersonORM.metadata
PRIVATE, CONTEXT, ALL_USERS = Audience.PRIVATE, Audience.CONTEXT, Audience.ALL_USERS


def _field(**changes: object) -> PersonalField:
    base = PersonalField(
        key="person.nickname",
        label="Nickname",
        columns=(Column("person", "name"),),
        audience_default=CONTEXT,
        audience_min=PRIVATE,
        audience_max=ALL_USERS,
    )
    return replace(base, **changes)  # pyright: ignore[reportArgumentType]


def test_the_registry_is_valid() -> None:
    assert problems(FIELDS, METADATA) == []


def test_a_valid_extra_field_is_accepted() -> None:
    assert problems([*FIELDS, _field()], METADATA) == []


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (_field(audience_default=PRIVATE, audience_min=CONTEXT), "narrower"),
        (_field(audience_default=ALL_USERS, audience_max=CONTEXT), "wider"),
        (
            _field(audience_default_for_unit_head=ALL_USERS, audience_max=CONTEXT),
            "unit head default",
        ),
        (
            _field(
                encrypted=True,
                audience_default=PRIVATE,
                audience_min=PRIVATE,
                audience_max=CONTEXT,
            ),
            "encrypted",
        ),
        (_field(key="Nickname"), "the key must look like"),
        (_field(columns=()), "no columns"),
        (_field(columns=(Column("nowhere", "name"),)), "no table"),
        (_field(columns=(Column("person", "nothing"),)), "no column `person.nothing`"),
        (
            _field(columns=(Column("contact", "value", where=("kind", "email")),)),
            "no column `contact.kind`",
        ),
    ],
)
def test_a_misconfigured_field_is_reported(field: PersonalField, expected: str) -> None:
    found = problems([field], METADATA)

    assert any(expected in line for line in found), found


def test_a_key_used_twice_is_reported() -> None:
    found = problems([_field(), _field()], METADATA)

    assert any("used twice" in line for line in found), found


def test_sensitivity_is_derived_from_the_widest_audience() -> None:
    assert get_field("passport.number").sensitive
    assert get_field("student.student_id").sensitive
    assert get_field("name_variant.fullname").sensitive
    assert not get_field("person.fullname").sensitive
    assert not get_field("passport.number").configurable
    assert get_field("person.fullname").configurable


def test_a_field_that_can_be_opened_is_never_encrypted() -> None:
    assert [f.key for f in FIELDS if f.encrypted and not f.sensitive] == []


def test_the_full_name_is_open_to_the_context_and_to_unit_heads_by_default() -> None:
    fullname = get_field("person.fullname")

    assert fullname.default_for(unit_head=False) == CONTEXT
    assert fullname.default_for(unit_head=True) == ALL_USERS
    assert fullname.audience_min == CONTEXT


def test_every_released_key_is_still_in_the_registry() -> None:
    current = {field.key for field in FIELDS}

    assert sorted(set(RELEASED) - current) == []


def test_no_released_field_became_visible_to_more_people_by_default() -> None:
    wider = [
        field.key
        for field in FIELDS
        if field.key in RELEASED
        and field.audience_default.rank > Audience(RELEASED[field.key]["default"]).rank
    ]

    assert wider == []


MESSAGE_TABLES = {
    "PersonData": "person",
    "PersonDelete": "person",
    "PersonLinkData": "person_account",
    "LinkAccountRequest": "person_account",
}


def _profile_messages() -> dict[str, type[BaseModel]]:
    return {
        name: value
        for name, value in vars(profile_messages).items()
        if inspect.isclass(value)
        and issubclass(value, BaseModel)
        and value.__module__ == profile_messages.__name__
        and not issubclass(value, MQEvent)
    }


def test_every_message_of_profile_is_mapped_to_its_table() -> None:
    assert sorted(_profile_messages()) == sorted(MESSAGE_TABLES)


def test_no_message_carries_a_field_that_may_stay_private() -> None:
    private = {
        (column.table, column.column)
        for field in FIELDS
        if field.audience_min == PRIVATE
        for column in field.columns
    }
    leaks = [
        f"{name}.{attr}"
        for name, message in _profile_messages().items()
        for attr in message.model_fields
        if (MESSAGE_TABLES[name], attr) in private
    ]

    assert leaks == []
