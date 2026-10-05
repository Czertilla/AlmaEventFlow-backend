import contextlib
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from logging import getLogger
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

logger = getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096


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


def _format_time(value: datetime, tz_name: str | None) -> str:
    """Renders the wall-clock time in ``tz_name`` when given and valid --
    Telegram's plain text has no per-viewer rendering, so it commits to the
    zone the stage's creator actually meant."""
    if tz_name:
        with contextlib.suppress(ZoneInfoNotFoundError, ValueError):
            value = value.astimezone(ZoneInfo(tz_name))
    return value.strftime("%H:%M")


def _format_date_time(
    event_date: date | None,
    stage_start: datetime | None,
    stage_tz: str | None,
    lang: str,
) -> str:
    if event_date is None:
        return ""
    text = _format_date(event_date, lang)
    if stage_start is not None:
        text += f", {_format_time(stage_start, stage_tz)}"
    return text


def _format_stage_time(stage: AnnouncementStage) -> str:
    time_part = _format_time(stage.start_at, stage.timezone)
    if stage.end_at is not None:
        time_part += f"–{_format_time(stage.end_at, stage.timezone)}"
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
        paragraphs.append(
            escape(_clip(request.event_description, limits.description))
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
