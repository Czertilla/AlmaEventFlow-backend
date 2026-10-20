from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from logging import getLogger
from typing import Any

from pydantic import ValidationError

from bot.tg.enum.callbacks import AttendanceCB
from bot.tg.text.localization import i18n_manager
from bot.tg.utils.links import map_url
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage
from core.schema.message.notify import TelegramButton
from core.utils.tz import as_aware, localize

logger = getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
MAX_RICH_LENGTH = 32768
QUOTE_FOLD_LENGTH = 300
_RICH_INDENT = "&nbsp;" * 3


@dataclass(frozen=True, slots=True)
class _Limits:
    description: int
    stage_description: int
    stages: int
    field: int = 200


_FIT_STEPS = (
    _Limits(description=1500, stage_description=300, stages=30),
    _Limits(description=700, stage_description=100, stages=15),
    _Limits(description=250, stage_description=0, stages=8),
    _Limits(description=0, stage_description=0, stages=4, field=100),
    _Limits(description=0, stage_description=0, stages=0, field=60),
)


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(limit - 1, 0)].rstrip() + "…"

_MONTHS_GENITIVE = {
    "ru": (
        "",
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ),
    "en": (
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}


def _format_date(value: date, lang: str) -> str:
    months = _MONTHS_GENITIVE.get(lang, _MONTHS_GENITIVE["ru"])
    return f"{value.day} {months[value.month]} {value.year}"


def _localize(value: datetime, tz_name: str | None) -> datetime:
    return localize(value, tz_name)


def _format_time(value: datetime, tz_name: str | None) -> str:
    return _localize(value, tz_name).strftime("%H:%M")


def _tg_time(value: datetime, fmt: str, fallback: str) -> str:
    """A date/time Telegram shows in each reader's own zone. ``fallback`` is
    what clients without support, and the plain text, show: the time in the
    zone the stage's creator meant."""
    unix = int(as_aware(value).timestamp())
    return f'<tg-time unix="{unix}" format="{fmt}">{fallback}</tg-time>'


def _format_date_time(
    event_date: date | None,
    stage_start: datetime | None,
    stage_tz: str | None,
    lang: str,
) -> str:
    if stage_start is not None:
        local = _localize(stage_start, stage_tz)
        day = event_date or local.date()
        fallback = f"{_format_date(day, lang)}, {local.strftime('%H:%M')}"
        return _tg_time(stage_start, "wDt", fallback)
    if event_date is not None:
        return _format_date(event_date, lang)
    return ""


def _format_stage_time(stage: AnnouncementStage) -> str:
    time_part = _tg_time(
        stage.start_at, "t", _format_time(stage.start_at, stage.timezone)
    )
    if stage.end_at is None:
        return time_part
    if _local_day(stage.end_at, stage.timezone) != _local_day(
        stage.start_at, stage.timezone
    ):
        end = _stage_moment(stage.end_at, stage.timezone)
    else:
        end = _tg_time(
            stage.end_at, "t", _format_time(stage.end_at, stage.timezone)
        )
    return f"{time_part}–{end}"


def _local_day(value: datetime, tz_name: str | None) -> date:
    return _localize(value, tz_name).date()


def _is_multi_day(stages: list[AnnouncementStage]) -> bool:
    return len({_local_day(stage.start_at, stage.timezone) for stage in stages}) > 1


def _by_day(
    stages: list[AnnouncementStage],
) -> list[tuple[date, list[AnnouncementStage]]]:
    days: list[tuple[date, list[AnnouncementStage]]] = []
    for stage in stages:
        day = _local_day(stage.start_at, stage.timezone)
        if days and days[-1][0] == day:
            days[-1][1].append(stage)
        else:
            days.append((day, [stage]))
    return days


def _day_label(day: date, first: AnnouncementStage, lang: str) -> str:
    return _tg_time(first.start_at, "wD", _format_date(day, lang))


def _free_text(value: str, *, rich: bool) -> str:
    escaped = escape(value)
    return "<br>".join(escaped.splitlines()) if rich else escaped


async def build_announcement_text(
    request: AnnouncementRequest, lang: str | None = None
) -> str:
    """Renders a group-chat announcement from raw structured data via i18n
    templates -- ``event``-service only gathers facts, this is the only place
    that decides layout/formatting/language. Dynamic values are HTML-escaped
    individually; the surrounding markup lives in the translation strings.
    Free text is trimmed step by step until the result fits one Telegram
    message, so a long description never makes the whole send fail."""
    return await _fit(request, lang, _render, MAX_MESSAGE_LENGTH)


async def build_announcement_rich(
    request: AnnouncementRequest, lang: str | None = None
) -> str:
    """The same announcement as the HTML of a Telegram rich message (Bot API
    10.1): headings and paragraphs, and an event that spans several days gets
    a divider with the date between the days. ``build_announcement_text``
    stays the fallback for when Telegram rejects it."""
    return await _fit(request, lang, _render_rich, MAX_RICH_LENGTH)


async def _fit(
    request: AnnouncementRequest,
    lang: str | None,
    render: Callable[[AnnouncementRequest, str | None, _Limits], Awaitable[str]],
    max_length: int,
) -> str:
    text = ""
    for step, limits in enumerate(_FIT_STEPS):
        text = await render(request, lang, limits)
        if len(text) <= max_length:
            if step:
                logger.info(
                    "announcement for event %s trimmed to %d characters "
                    "(fit step %d)",
                    request.event_id,
                    len(text),
                    step,
                )
            return text
    logger.warning(
        "announcement for event %s is still %d characters after trimming",
        request.event_id,
        len(text),
    )
    return text


async def _title(request: AnnouncementRequest, lang: str, limits: _Limits) -> str:
    event_name = escape(_clip(request.event_name, limits.field))
    if request.action_url:
        return await i18n_manager.get(
            "announcement.title_linked",
            lang=lang,
            event_name=event_name,
            action_url=escape(request.action_url),
        )
    return await i18n_manager.get(
        "announcement.title", lang=lang, event_name=event_name
    )


def _location_link(request: AnnouncementRequest, limits: _Limits) -> str:
    label = _clip(request.location or "", limits.field)
    url = map_url(label, request.location_lat, request.location_lon)
    return f'<a href="{escape(url)}">{escape(label)}</a>'


async def _meta_lines(
    request: AnnouncementRequest, lang: str, limits: _Limits
) -> list[str]:
    stage_start = request.stages[0].start_at if request.stages else None
    stage_tz = request.stages[0].timezone if request.stages else None
    meta_lines: list[str] = []
    date_time = _format_date_time(request.event_date, stage_start, stage_tz, lang)
    if date_time:
        meta_lines.append(
            await i18n_manager.get("announcement.date", lang=lang, date=date_time)
        )
    if request.location:
        meta_lines.append(
            await i18n_manager.get(
                "announcement.location",
                lang=lang,
                location=_location_link(request, limits),
            )
        )
    if request.organizer:
        meta_lines.append(
            await i18n_manager.get(
                "announcement.organizer",
                lang=lang,
                organizer=escape(_clip(request.organizer, limits.field)),
            )
        )
    return meta_lines


async def _description(
    request: AnnouncementRequest, lang: str, limits: _Limits, *, rich: bool
) -> str | None:
    if not request.event_description or not limits.description:
        return None
    description = _clip(request.event_description, limits.description)
    key = (
        "announcement.description_long"
        if len(description) > QUOTE_FOLD_LENGTH
        else "announcement.description"
    )
    return await i18n_manager.get(
        key, lang=lang, description=_free_text(description, rich=rich)
    )


async def _stage_lines(
    stages: list[AnnouncementStage], lang: str, limits: _Limits, *, rich: bool
) -> list[str]:
    lines: list[str] = []
    for stage in stages:
        lines.append(
            await i18n_manager.get(
                "announcement.stage_line",
                lang=lang,
                name=escape(_clip(stage.name, limits.field)),
                time=_format_stage_time(stage),
            )
        )
        if stage.description and limits.stage_description:
            note = _free_text(
                _clip(stage.description, limits.stage_description), rich=rich
            )
            if rich:
                lines.append(f"{_RICH_INDENT}<i>{note}</i>")
            else:
                lines.append(
                    await i18n_manager.get(
                        "announcement.stage_description",
                        lang=lang,
                        description=note,
                    )
                )
    return lines


async def _render(
    request: AnnouncementRequest, lang: str | None, limits: _Limits
) -> str:
    lang = lang or i18n_manager.default_lang
    paragraphs = [await _title(request, lang, limits)]

    meta_lines = await _meta_lines(request, lang, limits)
    if meta_lines:
        paragraphs.append("\n".join(meta_lines))

    description = await _description(request, lang, limits, rich=False)
    if description:
        paragraphs.append(description)

    shown_stages = request.stages[: limits.stages]
    if shown_stages:
        multi_day = _is_multi_day(request.stages)
        stage_lines = [await i18n_manager.get("announcement.stages_header", lang=lang)]
        for day, group in _by_day(shown_stages):
            if multi_day:
                stage_lines.append(
                    await i18n_manager.get(
                        "announcement.stage_day",
                        lang=lang,
                        date=_day_label(day, group[0], lang),
                    )
                )
            stage_lines.extend(await _stage_lines(group, lang, limits, rich=False))
        hidden = len(request.stages) - len(shown_stages)
        if hidden:
            stage_lines.append(
                await i18n_manager.get(
                    "announcement.stages_more", lang=lang, rest=hidden
                )
            )
        paragraphs.append("\n".join(stage_lines))

    paragraphs.append(await i18n_manager.get("announcement.cta", lang=lang))

    return "\n\n".join(paragraphs)


async def _render_rich(
    request: AnnouncementRequest, lang: str | None, limits: _Limits
) -> str:
    lang = lang or i18n_manager.default_lang
    blocks = [f"<h3>{await _title(request, lang, limits)}</h3>"]

    meta_lines = await _meta_lines(request, lang, limits)
    if meta_lines:
        blocks.append("<p>" + "<br>".join(meta_lines) + "</p>")

    description = await _description(request, lang, limits, rich=True)
    if description:
        blocks.append(description)

    shown_stages = request.stages[: limits.stages]
    if shown_stages:
        multi_day = _is_multi_day(request.stages)
        header = await i18n_manager.get("announcement.stages_header", lang=lang)
        blocks.append(f"<h4>{header}</h4>")
        for index, (day, group) in enumerate(_by_day(shown_stages)):
            if multi_day:
                if index:
                    blocks.append("<hr/>")
                blocks.append(f"<h5>{_day_label(day, group[0], lang)}</h5>")
            lines = await _stage_lines(group, lang, limits, rich=True)
            blocks.append("<p>" + "<br>".join(lines) + "</p>")
        hidden = len(request.stages) - len(shown_stages)
        if hidden:
            more = await i18n_manager.get(
                "announcement.stages_more", lang=lang, rest=hidden
            )
            blocks.append(f"<p>{more}</p>")

    cta = await i18n_manager.get("announcement.cta", lang=lang)
    blocks.append(f"<p>{cta}</p>")

    return "".join(blocks)


async def build_announcement_buttons(
    request: AnnouncementRequest, lang: str | None = None
) -> list[list[TelegramButton]]:
    lang = lang or i18n_manager.default_lang
    rows = [
        [
            TelegramButton(
                text=await i18n_manager.get("attendance.button_yes", lang=lang),
                callback_data=AttendanceCB(
                    event_id=request.event_id, decision="yes"
                ).pack(),
                style="success",
            ),
            TelegramButton(
                text=await i18n_manager.get("attendance.button_no", lang=lang),
                callback_data=AttendanceCB(
                    event_id=request.event_id, decision="no"
                ).pack(),
                style="danger",
            ),
        ]
    ]
    if request.action_url:
        rows.append(
            [
                TelegramButton(
                    text=await i18n_manager.get("button.open_event", lang=lang),
                    url=request.action_url,
                )
            ]
        )
    return rows


MAX_CHANGE_LINES = 8
CHANGE_VALUE_LIMIT = 100


def request_from_payload(
    payload: dict[str, Any] | None,
) -> AnnouncementRequest | None:
    if not payload:
        return None
    try:
        return AnnouncementRequest.model_validate(payload)
    except ValidationError:
        return None


def _stage_moment(value: datetime, tz_name: str | None) -> str:
    fallback = _localize(value, tz_name).strftime("%d.%m %H:%M")
    return _tg_time(value, "dt", fallback)


def _stage_span(stage: AnnouncementStage) -> str:
    span = _stage_moment(stage.start_at, stage.timezone)
    if stage.end_at is not None:
        span += "–" + _tg_time(
            stage.end_at, "t", _format_time(stage.end_at, stage.timezone)
        )
    return span


async def _scalar_change(
    key: str, old: str | None, new: str | None, lang: str
) -> str:
    nothing = await i18n_manager.get("announcement.nothing", lang=lang)
    return await i18n_manager.get(
        key,
        lang=lang,
        old=escape(_clip(old, CHANGE_VALUE_LIMIT)) if old else nothing,
        new=escape(_clip(new, CHANGE_VALUE_LIMIT)) if new else nothing,
    )


async def _stage_changes(
    old: list[AnnouncementStage], new: list[AnnouncementStage], lang: str
) -> list[str]:
    before = {stage.name: stage for stage in old}
    after = {stage.name for stage in new}
    lines: list[str] = []
    for stage in new:
        name = escape(_clip(stage.name, CHANGE_VALUE_LIMIT))
        previous = before.get(stage.name)
        if previous is None:
            lines.append(
                await i18n_manager.get(
                    "announcement.change_stage_added",
                    lang=lang,
                    name=name,
                    time=_stage_span(stage),
                )
            )
        elif (previous.start_at, previous.end_at) != (
            stage.start_at,
            stage.end_at,
        ):
            lines.append(
                await i18n_manager.get(
                    "announcement.change_stage_moved",
                    lang=lang,
                    name=name,
                    old=_stage_span(previous),
                    new=_stage_span(stage),
                )
            )
        elif (previous.description or "") != (stage.description or ""):
            lines.append(
                await i18n_manager.get(
                    "announcement.change_stage_edited", lang=lang, name=name
                )
            )
    for stage in old:
        if stage.name not in after:
            lines.append(
                await i18n_manager.get(
                    "announcement.change_stage_removed",
                    lang=lang,
                    name=escape(_clip(stage.name, CHANGE_VALUE_LIMIT)),
                )
            )
    return lines


async def describe_changes(
    old: AnnouncementRequest, new: AnnouncementRequest, lang: str
) -> list[str]:
    """What a reader of the announcement would notice between two versions of
    it, one line each. Only what the announcement shows is compared."""

    def day(value: date | None) -> str | None:
        return _format_date(value, lang) if value else None

    lines: list[str] = []
    if old.event_name != new.event_name:
        lines.append(
            await _scalar_change(
                "announcement.change_name", old.event_name, new.event_name, lang
            )
        )
    if old.event_date != new.event_date:
        lines.append(
            await _scalar_change(
                "announcement.change_date",
                day(old.event_date),
                day(new.event_date),
                lang,
            )
        )
    if (old.location or None) != (new.location or None):
        lines.append(
            await _scalar_change(
                "announcement.change_location", old.location, new.location, lang
            )
        )
    if (old.organizer or None) != (new.organizer or None):
        lines.append(
            await _scalar_change(
                "announcement.change_organizer",
                old.organizer,
                new.organizer,
                lang,
            )
        )
    if (old.event_description or "") != (new.event_description or ""):
        lines.append(
            await i18n_manager.get("announcement.change_description", lang=lang)
        )
    lines.extend(await _stage_changes(old.stages, new.stages, lang))
    return lines


async def build_update_notice(
    previous: AnnouncementRequest | None,
    request: AnnouncementRequest,
    lang: str | None = None,
    *,
    detailed: bool,
) -> str:
    """The reply posted under an announcement that was just edited. Brief: it
    only says "updated" (the quoted announcement names the event). Detailed:
    it names the event, lists what changed when the earlier version is known,
    and asks everybody to re-check their attendance mark."""
    lang = lang or i18n_manager.default_lang
    if not detailed:
        return await i18n_manager.get("announcement.updated", lang=lang)
    title = await i18n_manager.get(
        "announcement.updated_title",
        lang=lang,
        event_name=escape(_clip(request.event_name, 200)),
    )
    lines = await describe_changes(previous, request, lang) if previous else []
    if len(lines) > MAX_CHANGE_LINES:
        rest = len(lines) - MAX_CHANGE_LINES
        lines = [
            *lines[:MAX_CHANGE_LINES],
            await i18n_manager.get(
                "announcement.changes_more", lang=lang, rest=rest
            ),
        ]
    cta = await i18n_manager.get("announcement.update_cta", lang=lang)
    return "\n".join([title, *lines]) + "\n\n" + cta
