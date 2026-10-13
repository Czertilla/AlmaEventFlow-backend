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
    "table",
    "td",
    "tg-time",
    "tr",
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


async def test_the_rich_schedule_is_a_table_with_the_time_in_the_first_column() -> None:
    request = _request(stages=[_day_stage("Doors", 1), _day_stage("Talk", 1, 11)])

    html = await build_announcement_rich(request, lang="en")

    assert html.count("<table compact>") == 1
    rows = html.split("<tr>")[1:]
    assert len(rows) == 2
    for row, name in zip(rows, ("Doors", "Talk"), strict=True):
        time_cell, name_cell = row.split("</td><td>")
        assert time_cell.startswith("<td><tg-time")
        assert name_cell.startswith(f"<b>{name}</b></td></tr>")


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
    assert html.count("<table compact>") == 3
    for label in ("1 May 2026", "2 May 2026", "3 May 2026"):
        assert f'format="wD">{label}</tg-time></h5>' in html
    assert html.index("1 May 2026</tg-time></h5>") < html.index("Doors")
    assert html.index("Doors") < html.index("<hr/>")
    assert html.index("<hr/>") < html.index("2 May 2026</tg-time></h5>")


async def test_a_stage_description_is_a_row_under_its_stage() -> None:
    request = _request(
        stages=[_day_stage("Talk", 1, description="Line one\nLine <two>")]
    )

    html = await build_announcement_rich(request, lang="en")

    assert (
        '<tr><td colspan="2"><i>Line one<br>Line &lt;two&gt;</i></td></tr>' in html
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
    assert "<b><tr>" not in html
    assert not parser.unknown
    assert html.count("<tr>") == 1


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
    assert html.count("<tr>") == 30
