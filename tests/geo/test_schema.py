from uuid import uuid4

import pytest
from pydantic import ValidationError

from geo.schema.address import AddressCreate, AddressFields
from geo.schema.location import LocationCreate
from geo.search import MAX_TOKENS, tokenize


def test_tokenize_strips_punctuation_and_lowercases():
    assert tokenize("Тверская ул., 7к2 (Актовый)") == [
        "тверская",
        "ул",
        "7к2",
        "актовый",
    ]


def test_tokenize_drops_tsquery_syntax_characters():
    assert tokenize("a & b | !c :* (d) <-> e") == ["a", "b", "c", "d", "e"]


def test_tokenize_caps_token_count():
    assert len(tokenize(" ".join(["слово"] * 50))) == MAX_TOKENS


def test_compose_name_skips_blank_parts():
    fields = AddressFields(
        street="Арбат", house=" 10 ", building="", apartment=None
    )
    assert fields.compose_name() == "Арбат, 10"


def test_address_requires_name_or_parsed():
    with pytest.raises(ValidationError):
        AddressCreate(city_id=1)
    with pytest.raises(ValidationError):
        AddressCreate(city_id=1, name="  ", parsed=AddressFields())


def test_explicit_name_wins_over_parsed():
    address = AddressCreate(
        city_id=1,
        name="Главный корпус",
        parsed=AddressFields(street="Арбат", house="10"),
    )
    assert address.name == "Главный корпус"


def test_blank_location_name_becomes_none():
    assert LocationCreate(name="   ", address_id=uuid4()).name is None


def test_location_requires_address_or_spot():
    with pytest.raises(ValidationError):
        LocationCreate(name="Точка")


def test_location_combining_address_and_spot_requires_a_name():
    with pytest.raises(ValidationError):
        LocationCreate(address_id=uuid4(), spot={"lat": 55.75, "lon": 37.6})


def test_location_can_combine_address_and_spot_when_named():
    location = LocationCreate(
        name="Служебный вход",
        address_id=uuid4(),
        spot={"lat": 55.75, "lon": 37.6},
    )
    assert location.address_id is not None and location.spot is not None
