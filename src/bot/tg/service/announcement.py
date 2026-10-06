import contextlib
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from logging import getLogger
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError

from bot.tg.enum.callbacks import AttendanceCB
from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage
from core.schema.message.notify import TelegramButton

logger = getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
QUOTE_FOLD_LENGTH = 300


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
    if tz_name:
        with contextlib.suppress(ZoneInfoNotFoundError, ValueError):
            return value.astimezone(ZoneInfo(tz_name))
    return value


def _format_time(value: datetime, tz_name: str | None) -> str:
    return _localize(value, tz_name).strftime("%H:%M")


def _tg_time(value: datetime, fmt: str, fallback: str) -> str:
    """A date/time Telegram shows in each reader's own zone. ``fallback`` is
    what clients without support, and the plain text, show: the time in the
    zone the stage's creator meant."""
    unix = int(value.timestamp())
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
    if stage.end_at is not None:
        time_part += "–" + _tg_time(
            stage.end_at, "t", _format_time(stage.end_at, stage.timezone)
        )
    return time_part


async def build_announcement_text(
    request: AnnouncementRequest, lang: str | None = None
) -> str:
    """Renders a group-chat announcement from raw structured data via i18n
    templates -- ``event``-service only gathers facts, this is the only place
    that decides layout/formatting/language. Dynamic values are HTML-escaped
    individually; the surrounding markup lives in the translation strings.
    Free text is trimmed step by step until the result fits one Telegram
    message, so a long description never makes the whole send fail."""
    text = ""
    for step, limits in enumerate(_FIT_STEPS):
        text = await _render(request, lang, limits)
        if len(text) <= MAX_MESSAGE_LENGTH:
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


async def _render(
    request: AnnouncementRequest, lang: str | None, limits: _Limits
) -> str:
    lang = lang or i18n_manager.default_lang
    paragraphs: list[str] = []

    if request.action_url:
        paragraphs.append(
            await i18n_manager.get(
                "announcement.title_linked",
                lang=lang,
                event_name=escape(_clip(request.event_name, limits.field)),
                action_url=escape(request.action_url),
            )
        )
    else:
        paragraphs.append(
            await i18n_manager.get(
                "announcement.title",
                lang=lang,
                event_name=escape(_clip(request.event_name, limits.field)),
            )
        )

    stage_start = request.stages[0].start_at if request.stages else None
    stage_tz = request.stages[0].timezone if request.stages else None
    meta_lines = []
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
                location=escape(_clip(request.location, limits.field)),
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
    if meta_lines:
        paragraphs.append("\n".join(meta_lines))

    if request.event_description and limits.description:
        description = _clip(request.event_description, limits.description)
        key = (
            "announcement.description_long"
            if len(description) > QUOTE_FOLD_LENGTH
            else "announcement.description"
        )
        paragraphs.append(
            await i18n_manager.get(key, lang=lang, description=escape(description))
        )

    shown_stages = request.stages[: limits.stages]
    if shown_stages:
        stage_lines = [await i18n_manager.get("announcement.stages_header", lang=lang)]
        for stage in shown_stages:
            stage_lines.append(
                await i18n_manager.get(
                    "announcement.stage_line",
                    lang=lang,
                    name=escape(_clip(stage.name, limits.field)),
                    time=_format_stage_time(stage),
                )
            )
            if stage.description and limits.stage_description:
                stage_lines.append(
                    await i18n_manager.get(
                        "announcement.stage_description",
                        lang=lang,
                        description=escape(
                            _clip(stage.description, limits.stage_description)
                        ),
                    )
                )
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
        lines = lines[:MAX_CHANGE_LINES] + [
            await i18n_manager.get(
                "announcement.changes_more", lang=lang, rest=rest
            )
        ]
    cta = await i18n_manager.get("announcement.update_cta", lang=lang)
    return "\n".join([title, *lines]) + "\n\n" + cta
