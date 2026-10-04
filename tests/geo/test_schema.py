import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from geo.api.v1.schema.address import AddressCreate, AddressFields, AddressRead
from geo.api.v1.schema.location import LocationCreate, LocationRead
from geo.api.v1.schema.point import Point
from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO
from geo.dto.point import PointDTO
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
    fields = AddressFields(street="Арбат", house=" 10 ", building="", apartment=None)
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


NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


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


def test_address_response_exposes_a_geo_uri_for_its_spot():
    dto = AddressDTO(
        id=uuid4(),
        city_id=1,
        name="Арбат, 10",
        spot=PointDTO(lat=55.75, lon=37.6),
        parsed=None,
        source=None,
        created_at=NOW,
        edited_at=None,
    )

    assert AddressRead.from_dto(dto).map_uri == "geo:55.75,37.6"


def test_location_response_falls_back_to_its_address_for_map_uri_and_name():
    address = AddressDTO(
        id=uuid4(),
        city_id=1,
        name="Арбат, 10",
        spot=PointDTO(lat=55.75, lon=37.6),
        parsed=None,
        source=None,
        created_at=NOW,
        edited_at=None,
    )
    dto = LocationDTO(
        id=uuid4(),
        name=None,
        address_id=address.id,
        spot=None,
        address=address,
        created_at=NOW,
        edited_at=None,
    )

    location = LocationRead.from_dto(dto)

    assert location.map_uri == "geo:55.75,37.6"
    assert location.display_name == "Арбат, 10"


def test_spot_converts_to_a_point_dto_when_the_request_is_converted():
    address = AddressCreate(
        city_id=1, name="Арбат", spot=Point(lat=55.75, lon=37.6)
    ).to_dto()

    assert address.spot == PointDTO(lat=55.75, lon=37.6)
