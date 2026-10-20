from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from support.geocoder import (
    DatedStubGeocoder,
    Maker,
    Published,
    StubGeocoder,
    count_rows,
    moscow_house,
    row_of,
    store_address,
)

from geo.bootstrap.refresh import refresh
from geo.dto.location import LocationCreateDTO
from geo.geocoder.base import GeocoderError
from geo.models.address import AddressORM
from geo.service.location import LocationService
from geo.uow.location import LocationUOW

MOSCOW = ("Россия", "Москва", "Москва")
ROSTOV = ("Россия", "Ярославская область", "Ростов")
CENTER = (55.7583, 37.6116)


def _days_ago(days: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def _photon_row(
    sessionmaker_: Maker,
    house: str = "7",
    *,
    days: float = 40,
    city: tuple[str, str, str] = MOSCOW,
    point: tuple[float, float] = CENTER,
) -> AddressORM:
    return await store_address(
        sessionmaker_,
        city,
        "Тверская улица",
        house,
        point,
        source="photon",
        synced_at=_days_ago(days),
    )


def _found(house: str = "7", **options: Any):
    return moscow_house("Тверская улица", house, **options)


async def _ids(sessionmaker_: Maker) -> set[Any]:
    async with sessionmaker_() as session:
        return set((await session.execute(select(AddressORM.id))).scalars())


async def test_a_row_that_is_found_again_takes_the_current_data_and_a_new_date(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    row = await _photon_row(sessionmaker_)
    geocoder = StubGeocoder(
        [_found(source_id="way/5", lat=CENTER[0] + 0.0002, lon=CENTER[1])]
    )

    report = await refresh(geocoder, sessionmaker=sessionmaker_)

    after = await row_of(sessionmaker_, row.id)
    assert (report.checked, report.confirmed, report.missing) == (1, 1, 0)
    assert geocoder.calls[0][0] == "Тверская улица, 7, Москва"
    assert (geocoder.calls[0][1].lat, geocoder.calls[0][1].lon) == CENTER  # pyright: ignore[reportOptionalMemberAccess]
    assert after.source_id == "way/5"
    assert after.synced_at and after.synced_at > _days_ago(1)
    assert after.edited_at is not None
    assert row.synced_at and after.synced_at > row.synced_at
    assert await count_rows(sessionmaker_, AddressORM) == 1


async def test_a_row_that_was_seen_lately_is_not_asked(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _photon_row(sessionmaker_, days=1)
    geocoder = StubGeocoder()

    report = await refresh(geocoder, sessionmaker=sessionmaker_)

    assert geocoder.calls == []
    assert report.checked == 0


async def test_only_rows_of_the_provider_are_asked(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await store_address(
        sessionmaker_, MOSCOW, "Тверская улица", "7", CENTER, synced_at=_days_ago(99)
    )
    manual = await store_address(
        sessionmaker_, MOSCOW, "Тверская улица", "9", CENTER, source=None
    )
    geocoder = StubGeocoder()

    report = await refresh(geocoder, sessionmaker=sessionmaker_)

    assert (report.checked, geocoder.calls) == (0, [])
    assert (await row_of(sessionmaker_, manual.id)).synced_at is not None


async def test_data_built_before_the_last_confirmation_cannot_have_changed(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _photon_row(sessionmaker_, "7", days=5)
    old = await _photon_row(sessionmaker_, "9", days=20)
    geocoder = DatedStubGeocoder([_found("9")], built=_days_ago(10))

    report = await refresh(
        geocoder, sessionmaker=sessionmaker_, older_than=timedelta(days=1)
    )

    assert report.checked == 1
    assert [call[0] for call in geocoder.calls] == ["Тверская улица, 9, Москва"]
    assert (await row_of(sessionmaker_, old.id)).synced_at > _days_ago(1)  # pyright: ignore[reportOptionalOperand]


async def test_an_unknown_build_date_falls_back_to_the_age_alone(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _photon_row(sessionmaker_, days=5)
    geocoder = DatedStubGeocoder([_found()], built=None)

    report = await refresh(
        geocoder, sessionmaker=sessionmaker_, older_than=timedelta(days=1)
    )

    assert report.checked == 1


async def test_a_row_that_is_not_found_is_reported_and_kept(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    row = await _photon_row(sessionmaker_, days=100)
    geocoder = StubGeocoder([_found("99")])

    report = await refresh(geocoder, sessionmaker=sessionmaker_, prune=False)

    after = await row_of(sessionmaker_, row.id)
    assert (report.missing, report.confirmed, report.pruned) == (1, 0, 0)
    assert after.synced_at == row.synced_at
    assert after.name == row.name


async def test_a_house_found_too_far_away_is_not_the_same_house(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _photon_row(sessionmaker_)
    geocoder = StubGeocoder([_found(lat=CENTER[0] + 0.02)])

    report = await refresh(geocoder, sessionmaker=sessionmaker_)

    assert (report.missing, report.confirmed) == (1, 0)


async def test_a_missing_row_is_deleted_only_after_it_stayed_unseen_long_enough(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    gone = await _photon_row(sessionmaker_, "7", days=100)
    young = await _photon_row(sessionmaker_, "9", days=40)
    geocoder = StubGeocoder([_found("99")])

    report = await refresh(
        geocoder, sessionmaker=sessionmaker_, prune=True, prune_after=timedelta(days=90)
    )

    assert (report.missing, report.pruned) == (2, 1)
    assert await _ids(sessionmaker_) == {young.id}
    deleted = [str(payload[0]) for name, payload in published if "deleted" in name]
    assert deleted == [str(gone.id)]


async def test_a_row_a_location_points_at_is_never_deleted(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    row = await _photon_row(sessionmaker_, days=100)
    await LocationService(LocationUOW(sessionmaker_)).create(
        LocationCreateDTO(name="Актовый зал", address_id=row.id)
    )

    report = await refresh(
        StubGeocoder([]), sessionmaker=sessionmaker_, prune=True
    )

    assert (report.missing, report.pruned) == (1, 0)
    assert await _ids(sessionmaker_) == {row.id}


async def test_a_twin_from_another_source_makes_the_row_a_duplicate(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await store_address(
        sessionmaker_, ROSTOV, "Тверская улица", "7", (CENTER[0] + 0.0004, CENTER[1])
    )
    duplicate = await _photon_row(sessionmaker_)
    geocoder = StubGeocoder()

    kept = await refresh(geocoder, sessionmaker=sessionmaker_)
    pruned = await refresh(geocoder, sessionmaker=sessionmaker_, prune=True)

    assert (kept.duplicates, kept.pruned, kept.checked) == (1, 0, 0)
    assert (pruned.duplicates, pruned.pruned) == (1, 1)
    assert geocoder.calls == []
    assert duplicate.id not in await _ids(sessionmaker_)
    assert await count_rows(sessionmaker_, AddressORM) == 1


async def test_a_twin_far_away_or_of_another_house_is_no_duplicate(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await store_address(
        sessionmaker_, ROSTOV, "Тверская улица", "7", (CENTER[0] + 0.01, CENTER[1])
    )
    await store_address(
        sessionmaker_, ROSTOV, "Тверская улица", "9", (CENTER[0] + 0.0004, CENTER[1])
    )
    await _photon_row(sessionmaker_)

    report = await refresh(
        StubGeocoder([_found()]), sessionmaker=sessionmaker_, prune=True
    )

    assert (report.duplicates, report.confirmed, report.pruned) == (0, 1, 0)


async def test_a_geocoder_that_keeps_failing_stops_the_run_early(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    for house in range(1, 6):
        await _photon_row(sessionmaker_, str(house))
    geocoder = StubGeocoder(error=GeocoderError("HTTP 503"))

    report = await refresh(geocoder, sessionmaker=sessionmaker_, prune=True)

    assert (report.errors, report.aborted, report.pruned) == (3, True, 0)
    assert len(geocoder.calls) == 3
    assert await count_rows(sessionmaker_, AddressORM) == 5


async def test_one_failure_among_answers_does_not_stop_the_run(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    for house in ("7", "9"):
        await _photon_row(sessionmaker_, house)
    geocoder = StubGeocoder([_found("9")])
    original = geocoder.search
    calls = 0

    async def flaky(query: str, *, near: Any, limit: int):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError
        return await original(query, near=near, limit=limit)

    geocoder.search = flaky  # pyright: ignore[reportAttributeAccessIssue]

    report = await refresh(geocoder, sessionmaker=sessionmaker_)

    assert (report.errors, report.aborted, report.confirmed) == (1, False, 1)


async def test_a_run_asks_at_most_the_limit_and_the_next_run_goes_on(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    for house in ("1", "2", "3"):
        await _photon_row(sessionmaker_, house)
    geocoder = StubGeocoder([_found("1"), _found("2"), _found("3")])

    first = await refresh(geocoder, sessionmaker=sessionmaker_, limit=2)
    second = await refresh(geocoder, sessionmaker=sessionmaker_, limit=2)

    assert (first.checked, second.checked) == (2, 1)
    assert (first.confirmed, second.confirmed) == (2, 1)
