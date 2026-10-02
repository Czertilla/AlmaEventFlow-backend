import re
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import (
    ColumnElement,
    Select,
    String,
    case,
    func,
    literal,
    literal_column,
    select,
)

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.dto.pagination import PageParams

TS_CONFIG = literal_column("'russian'::regconfig")
WORD_SIMILARITY_THRESHOLD = "0.5"
MAX_TOKENS = 8

_TOKEN = re.compile(r"[^\W_]+")


def tokenize(query: str) -> list[str]:
    return _TOKEN.findall(query.lower())[:MAX_TOKENS]


def _tsquery(tokens: list[str], suffix: str = "") -> ColumnElement:
    return func.to_tsquery(
        TS_CONFIG, " & ".join(f"{token}{suffix}" for token in tokens)
    )


@dataclass(frozen=True)
class TextMatch:
    morphological: ColumnElement[bool]
    fuzzy: ColumnElement[bool]
    rank: ColumnElement[float]


def text_match(
    query: str, tsv: ColumnElement, text: ColumnElement
) -> TextMatch | None:
    tokens = tokenize(query)
    if not tokens:
        return None
    prefix = _tsquery(tokens, ":*")
    rank = (
        case((tsv.op("@@")(_tsquery(tokens)), 1.0), else_=0.0)
        + func.ts_rank(tsv, prefix, 2)
        + func.word_similarity(query, text)
    )
    return TextMatch(
        morphological=tsv.op("@@")(prefix),
        fuzzy=literal(query, String).op("<%")(text),
        rank=rank,
    )


async def search_page(
    repo: SQLAlchemyRepository,
    build: Callable[[ColumnElement[bool]], Select],
    match: TextMatch,
    pagination: PageParams,
    *,
    tie_break: tuple[ColumnElement, ...] = (),
    options=None,
):
    """Stemmed prefix match first; trigram similarity (typo tolerance) only
    when that finds nothing, so exact-ish queries aren't diluted by fuzzy
    hits."""
    await repo.execute(
        select(
            func.set_config(
                "pg_trgm.word_similarity_threshold",
                WORD_SIMILARITY_THRESHOLD,
                True,
            )
        )
    )
    for predicate in (match.morphological, match.fuzzy):
        base = build(predicate)
        total = (
            await repo.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        if not total:
            continue
        stmt = (
            base.order_by(match.rank.desc(), *tie_break)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        if options:
            stmt = stmt.options(*options)
        return (await repo.execute(stmt)).unique().scalars(), total
    return [], 0
