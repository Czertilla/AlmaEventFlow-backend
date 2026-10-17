import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from uuid import uuid4

import pytest
from aiocache import SimpleMemoryCache  # pyright: ignore[reportMissingTypeStubs]

from bot.tg.service.announcement import (
    build_announcement_rich,
    build_announcement_text,
)
from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

TELEGRAM_LIMIT = 4096
RICH_LIMIT = 32768
RICH_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "h3",
    "h4",
    "h5",
    "hr",
    "i",
    "p",
    "tg-time",
}
VOID_TAGS = {"br", "hr"}


@pytest.fixture(autouse=True)
def memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n_manager, "cache", SimpleMemoryCache())


def _request(**overrides: object) -> AnnouncementRequest:
    fields: dict[str, object] = {
        "collective_id": uuid4(),
        "event_id": uuid4(),
        "event_name": "Concert",
        "event_date": date(2026, 5, 1),
        "action_url": "https://example.test/event/1",
    }
    fields.update(overrides)
    return AnnouncementRequest(**fields)  # pyright: ignore[reportArgumentType]


def _stages(count: int, description: int) -> list[AnnouncementStage]:
    return [
        AnnouncementStage(
            name=f"Stage {number} " + "S" * 150,
            start_at=datetime(2026, 5, 1, 9, tzinfo=UTC),
            end_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
            description="x" * description,
        )
        for number in range(count)
    ]


async def test_short_announcement_keeps_everything() -> None:
    text = await build_announcement_text(
        _request(event_description="Bring a friend", stages=_stages(2, 20)), lang="ru"
    )

    assert "Bring a friend" in text
    assert text.count("Stage") == 2


async def test_oversized_announcement_fits_the_telegram_limit() -> None:
    request = _request(
        event_name="N" * 300,
        event_description="d" * 10_000,
        location="L" * 500,
        organizer="O" * 500,
        stages=_stages(40, 500),
    )

    text = await build_announcement_text(request, lang="ru")

    assert len(text) <= TELEGRAM_LIMIT


async def test_trimmed_announcement_keeps_markup_and_call_to_action() -> None:
    request = _request(event_description="d" * 10_000, stages=_stages(40, 500))

    text = await build_announcement_text(request, lang="ru")

    for tag in ("b", "a", "i"):
        opened = text.count(f"<{tag}>") + text.count(f"<{tag} ")
        assert opened == text.count(f"</{tag}>")
    assert text.endswith(await i18n_manager.get("announcement.cta", lang="ru"))


async def test_escaped_symbols_do_not_overflow_the_limit() -> None:
    request = _request(
        event_name="&" * 300,
        event_description="<" * 10_000,
        location="&" * 500,
        organizer="&" * 500,
        stages=_stages(40, 500),
    )

    text = await build_announcement_text(request, lang="ru")

    assert len(text) <= TELEGRAM_LIMIT


async def test_event_time_is_a_date_entity_each_reader_sees_in_their_zone() -> None:
    start = datetime(2026, 5, 1, 9, tzinfo=UTC)
    text = await build_announcement_text(
        _request(
            stages=[
                AnnouncementStage(
                    name="Doors", start_at=start, timezone="Asia/Almaty"
                )
            ]
        ),
        lang="en",
    )

    unix = int(start.timestamp())
    assert f'<tg-time unix="{unix}" format="wDt">1 May 2026, 14:00</tg-time>' in text
    assert f'<tg-time unix="{unix}" format="t">14:00</tg-time>' in text


async def test_stage_range_has_an_entity_for_each_end() -> None:
    start = datetime(2026, 5, 1, 9, tzinfo=UTC)
    end = datetime(2026, 5, 1, 10, 30, tzinfo=UTC)
    text = await build_announcement_text(
        _request(stages=[AnnouncementStage(name="Talk", start_at=start, end_at=end)]),
        lang="en",
    )

    assert f'format="t">09:00</tg-time>–<tg-time unix="{int(end.timestamp())}"' in text
    assert ">10:30</tg-time>" in text


async def test_an_event_without_stages_shows_just_the_date() -> None:
    text = await build_announcement_text(_request(), lang="en")

    assert "1 May 2026" in text
    assert "<tg-time" not in text


async def test_a_short_description_is_a_quote_and_a_long_one_folds() -> None:
    short = await build_announcement_text(
        _request(event_description="Bring a friend"), lang="en"
    )
    long = await build_announcement_text(
        _request(event_description="word " * 100), lang="en"
    )

    assert "<blockquote>Bring a friend</blockquote>" in short
    assert "<blockquote expandable>" in long
    assert "<blockquote>" not in long


def _day_stage(
    name: str, day: int, hour: int = 9, description: str | None = None
) -> AnnouncementStage:
    return AnnouncementStage(
        name=name,
        start_at=datetime(2026, 5, day, hour, tzinfo=UTC),
        end_at=datetime(2026, 5, day, hour + 1, tzinfo=UTC),
        description=description,
    )


class _RichStructure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unknown: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in RICH_TAGS:
            self.unknown.add(tag)
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag not in RICH_TAGS:
            self.unknown.add(tag)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack and self.stack[-1] == tag, f"unbalanced </{tag}>"
        self.stack.pop()


async def test_a_stage_line_starts_with_the_time_and_ends_with_the_name() -> None:
    text = await build_announcement_text(
        _request(stages=[_day_stage("Talk", 1)]), lang="en"
    )

    line = next(line for line in text.splitlines() if "Talk" in line)
    assert line.index("<tg-time") < line.index("Talk")
    assert line.endswith("<b>Talk</b>")


async def test_a_one_day_schedule_has_no_date_dividers() -> None:
    request = _request(stages=[_day_stage("Doors", 1), _day_stage("Talk", 1, 11)])

    text = await build_announcement_text(request, lang="en")
    rich = await build_announcement_rich(request, lang="en")

    assert 'format="wD"' not in text
    assert 'format="wD"' not in rich
    assert "<hr/>" not in rich


async def test_a_schedule_over_several_days_is_split_by_dates() -> None:
    request = _request(
        stages=[
            _day_stage("Doors", 1),
            _day_stage("Talk", 1, 11),
            _day_stage("Workshop", 2),
        ]
    )

    text = await build_announcement_text(request, lang="en")

    assert text.count('format="wD"') == 2
    assert 'format="wD">1 May 2026</tg-time>' in text
    assert 'format="wD">2 May 2026</tg-time>' in text
    assert text.index("1 May 2026</tg-time>") < text.index("Doors")
    assert text.index("Talk") < text.index("2 May 2026</tg-time>")
    assert text.index("2 May 2026</tg-time>") < text.index("Workshop")
    assert 'format="dt"' not in text


async def test_a_stage_that_ends_on_another_day_names_that_day() -> None:
    start = datetime(2026, 5, 1, 22, tzinfo=UTC)
    end = datetime(2026, 5, 2, 1, tzinfo=UTC)
    request = _request(
        stages=[AnnouncementStage(name="Party", start_at=start, end_at=end)]
    )

    text = await build_announcement_text(request, lang="en")
    rich = await build_announcement_rich(request, lang="en")

    for body in (text, rich):
        assert f'unix="{int(start.timestamp())}" format="t">22:00' in body
        assert f'unix="{int(end.timestamp())}" format="dt">02.05 01:00' in body


async def test_the_days_follow_the_zone_the_stages_were_planned_in() -> None:
    stages = [
        AnnouncementStage(
            name="Late",
            start_at=datetime(2026, 5, 1, 20, tzinfo=UTC),
            timezone="Asia/Almaty",
        ),
        AnnouncementStage(
            name="Next",
            start_at=datetime(2026, 5, 2, 9, tzinfo=UTC),
            timezone="Asia/Almaty",
        ),
    ]

    text = await build_announcement_text(_request(stages=stages), lang="en")
    rich = await build_announcement_rich(_request(stages=stages), lang="en")

    assert 'format="wD"' not in text
    assert "<hr/>" not in rich


async def test_the_rich_schedule_is_a_line_per_stage_with_the_time_first() -> None:
    request = _request(stages=[_day_stage("Doors", 1), _day_stage("Talk", 1, 11)])

    html = await build_announcement_rich(request, lang="en")

    assert "<table" not in html
    schedule = html.split("</h4>")[1].split("</p>")[0].removeprefix("<p>")
    lines = schedule.split("<br>")
    assert len(lines) == 2
    for line, name in zip(lines, ("Doors", "Talk"), strict=True):
        assert line.startswith("▫️ <tg-time")
        assert line.endswith(f"<b>{name}</b>")


async def test_a_rich_schedule_over_several_days_has_a_divider_between_days() -> None:
    request = _request(
        stages=[
            _day_stage("Doors", 1),
            _day_stage("Workshop", 2),
            _day_stage("Finale", 3),
        ]
    )

    html = await build_announcement_rich(request, lang="en")

    assert html.count("<hr/>") == 2
    assert "<table" not in html
    for label in ("1 May 2026", "2 May 2026", "3 May 2026"):
        assert f'format="wD">{label}</tg-time></h5>' in html
    assert html.index("1 May 2026</tg-time></h5>") < html.index("Doors")
    assert html.index("Doors") < html.index("<hr/>")
    assert html.index("<hr/>") < html.index("2 May 2026</tg-time></h5>")


async def test_a_stage_description_is_a_line_under_its_stage() -> None:
    request = _request(
        stages=[_day_stage("Talk", 1, description="Line one\nLine <two>")]
    )

    html = await build_announcement_rich(request, lang="en")

    assert (
        "<b>Talk</b><br>&nbsp;&nbsp;&nbsp;<i>Line one<br>Line &lt;two&gt;</i>" in html
    )


async def test_a_rich_description_keeps_its_line_breaks() -> None:
    html = await build_announcement_rich(
        _request(event_description="First\nSecond\r\nThird"), lang="en"
    )

    assert "<blockquote>First<br>Second<br>Third</blockquote>" in html


async def test_the_rich_announcement_is_balanced_and_uses_only_known_tags() -> None:
    request = _request(
        event_description="Bring a friend",
        location="Main hall",
        organizer="Choir",
        stages=[
            _day_stage("Doors", 1, description="Be early"),
            _day_stage("Workshop", 2),
        ],
    )

    for lang in ("ru", "en"):
        parser = _RichStructure()
        parser.feed(await build_announcement_rich(request, lang=lang))
        parser.close()

        assert not parser.stack
        assert not parser.unknown


async def test_the_rich_announcement_escapes_what_people_typed() -> None:
    html = await build_announcement_rich(
        _request(
            event_name="<b>&",
            location="<i>",
            stages=[_day_stage("<tr>", 1)],
        ),
        lang="en",
    )

    parser = _RichStructure()
    parser.feed(html)
    parser.close()
    assert "&lt;b&gt;&amp;" in html
    assert "&lt;tr&gt;" in html
    assert "<tr>" not in html
    assert not parser.unknown


async def test_an_oversized_rich_announcement_fits_the_rich_limit() -> None:
    request = _request(
        event_name="N" * 300,
        event_description="d" * 10_000,
        location="L" * 500,
        organizer="O" * 500,
        stages=_stages(40, 500),
    )

    html = await build_announcement_rich(request, lang="ru")

    assert len(html) <= RICH_LIMIT
    assert html.endswith(
        f"<p>{await i18n_manager.get('announcement.cta', lang='ru')}</p>"
    )


async def test_stages_beyond_the_shown_ones_are_counted_in_the_rich_text() -> None:
    request = _request(stages=_stages(40, 0))

    html = await build_announcement_rich(request, lang="en")

    assert "…and 10 more" in html
    assert html.count("<b>Stage ") == 30


async def test_a_location_with_a_point_links_to_it_on_the_map() -> None:
    request = _request(location="Main hall", location_lat=55.75, location_lon=37.62)

    for build in (build_announcement_text, build_announcement_rich):
        html = await build(request, lang="en")

        assert (
            '📍 <a href="https://yandex.ru/maps/?pt=37.620000,55.750000'
            '&amp;z=17&amp;l=map">Main hall</a>'
        ) in html


async def test_a_location_without_a_point_links_to_a_search_for_its_text() -> None:
    request = _request(location="ул. Пушкина, 10 & 2")

    for build in (build_announcement_text, build_announcement_rich):
        html = await build(request, lang="en")

        assert (
            '<a href="https://yandex.ru/maps/?text='
            "%D1%83%D0%BB.%20%D0%9F%D1%83%D1%88%D0%BA%D0%B8%D0%BD%D0%B0%2C%2010%20%26%202"
            '">ул. Пушкина, 10 &amp; 2</a>'
        ) in html


async def test_no_location_means_no_map_link() -> None:
    for build in (build_announcement_text, build_announcement_rich):
        html = await build(_request(), lang="en")

        assert "yandex.ru/maps" not in html
        assert "📍" not in html


async def test_a_half_known_point_is_not_a_point() -> None:
    html = await build_announcement_text(
        _request(location="Main hall", location_lat=55.75), lang="en"
    )

    assert "?text=Main%20hall" in html
    assert "pt=" not in html


async def test_what_people_typed_cannot_break_out_of_the_link() -> None:
    request = _request(location='"><b>x</b>')

    for build in (build_announcement_text, build_announcement_rich):
        html = await build(request, lang="en")
        parser = _RichStructure()
        parser.feed(html)
        parser.close()

        assert (
            '<a href="https://yandex.ru/maps/?text=%22%3E%3Cb%3Ex%3C%2Fb%3E">'
            "&quot;&gt;&lt;b&gt;x&lt;/b&gt;</a>"
        ) in html
        assert "<b>x</b>" not in html
        assert not parser.unknown


async def test_a_long_location_keeps_its_link_short_and_the_message_in_limit() -> None:
    request = _request(
        location="Ж" * 500,
        stages=_stages(40, 500),
        event_description="d" * 10_000,
    )

    text = await build_announcement_text(request, lang="ru")
    rich = await build_announcement_rich(request, lang="ru")

    assert len(text) <= TELEGRAM_LIMIT
    assert len(rich) <= RICH_LIMIT
    hrefs = re.findall(r'href="(https://yandex\.ru/maps[^"]*)"', text)
    assert len(hrefs) == 1
    assert len(hrefs[0]) < 800
