# ruff: noqa: RUF001
import pytest

from geo.dto.address import AddressFieldsDTO
from geo.identity import (
    address_key,
    box_around,
    house_key,
    meters_between,
    place_words,
    query_house,
    split_query,
    starts_like,
    stored_key,
    street_key,
    street_words,
)


@pytest.mark.parametrize(
    "one, other",
    [
        ("улица Баумана", "Баумана улица"),
        ("улица Баумана", "ул. Баумана"),
        ("Ленинский проспект", "Ленинский пр-т"),
        ("Ленинский проспект", "проспект  Ленинский"),
        ("Чёрная улица", "черная улица"),
        ("1-я Тверская-Ямская улица", "улица 1-я Тверская-Ямская"),
    ],
)
def test_one_street_has_one_key_whatever_the_spelling(one: str, other: str):
    assert street_key(one) == street_key(other)


@pytest.mark.parametrize(
    "one, other",
    [
        ("улица Ленина", "проспект Ленина"),
        ("Тверская улица", "Тверской проезд"),
        ("1-я Тверская-Ямская улица", "2-я Тверская-Ямская улица"),
    ],
)
def test_different_streets_keep_different_keys(one: str, other: str):
    assert street_key(one) != street_key(other)


@pytest.mark.parametrize(
    "one, other",
    [
        ("28 к1", "28к1"),
        ("28 корпус 1", "28к1"),
        ("28 корп. 1", "28к1"),
        ("28 А", "28а"),
        ("28A", "28а"),
        ("д. 7", "7"),
        ("дом 7", "7"),
        ("12 строение 3", "12с3"),
    ],
)
def test_one_house_has_one_key_whatever_the_spelling(one: str, other: str):
    assert house_key(one) == house_key(other)


@pytest.mark.parametrize(
    "one, other", [("28", "28а"), ("28/1", "28"), ("28к1", "28к2")]
)
def test_different_houses_keep_different_keys(one: str, other: str):
    assert house_key(one) != house_key(other)


def test_a_stored_key_reads_the_parsed_fields_before_the_name():
    parsed = AddressFieldsDTO(street="улица Баумана", house="43", building="2")

    assert stored_key("улица Баумана, 43, 2", parsed) == address_key(
        "Баумана ул.", "43"
    )


def test_a_manual_row_without_parsed_fields_is_read_from_its_name():
    assert stored_key("Тверская улица, 7", None) == address_key("Тверская улица", "7")
    assert stored_key("Тверская улица", None) == ("тверская улица", "")


@pytest.mark.parametrize(
    "text, words, house",
    [
        ("тверская 7 москва", ["тверская"], "7"),
        ("Тверская улица, д. 7", ["тверская", "улица", "д."], "7"),
        ("ленинский проспект 70 к 2", ["ленинский", "проспект"], "70к2"),
        ("ленинский проспект 70 корп. 2 москва", ["ленинский", "проспект"], "70к2"),
        ("1-я тверская-ямская 5", ["1-я", "тверская-ямская"], "5"),
        ("невский", ["невский"], None),
        ("москва", ["москва"], None),
    ],
)
def test_a_typed_query_is_split_into_street_words_and_a_house(
    text: str, words: list[str], house: str | None
):
    assert split_query(text) == (words, house)
    assert query_house(text) == house


def test_the_street_type_is_not_a_search_word():
    assert street_words(["улица", "баумана", "д."]) == ["баумана"]
    assert street_words(["1-я", "тверская-ямская", "ул"]) == ["1-я", "тверская-ямская"]


def test_distance_is_in_meters_and_symmetric():
    one = (55.7583, 37.6116)
    other = (55.7593, 37.6116)

    assert meters_between(*one, *other) == pytest.approx(111.2, abs=1.0)
    assert meters_between(*other, *one) == pytest.approx(meters_between(*one, *other))
    assert meters_between(*one, *one) == 0.0


def test_the_box_holds_the_circle_at_any_latitude():
    for lat in (0.0, 55.75, 69.0):
        south, west, north, east = box_around(lat, 30.0, 150.0)

        assert meters_between(lat, 30.0, north, 30.0) == pytest.approx(150.0, abs=1.0)
        assert meters_between(lat, 30.0, lat, east) == pytest.approx(150.0, abs=1.0)
        assert (south, west) < (lat, 30.0) < (north, east)


@pytest.mark.parametrize(
    "typed, name, expected",
    [
        ("суздаль", "суздаль", True),
        ("суздал", "суздаль", False),
        ("суз", "суздаль", False),
        ("уфа", "уфа", True),
        ("ростов", "ростов великий", True),
        ("ростов вели", "ростов великий", False),
        ("ростов великий", "ростов великий", True),
        ("великий", "ростов великий", False),
        ("ростов на дону", "ростов на дону", True),
        ("ростов на дону центр", "ростов на дону", False),
        ("", "суздаль", False),
    ],
)
def test_typed_words_begin_a_settlement_name_only_as_whole_words(
    typed: str, name: str, expected: bool
):
    assert starts_like(typed.split(), name.split()) is expected


def test_place_words_ignore_case_yo_and_hyphens():
    assert place_words("Ростов-на-Дону") == ["ростов", "на", "дону"]
    assert place_words("ЧЁРНАЯ  речка") == ["черная", "речка"]
