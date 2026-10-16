import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from geoalchemy2 import WKTElement
from sqlalchemy import (
    ColumnClause,
    ColumnElement,
    Float,
    Select,
    String,
    case,
    func,
    literal,
    literal_column,
    select,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.dto.pagination import PageParams
from geo.dto.point import PointDTO

Expression = ColumnElement[Any] | InstrumentedAttribute[Any]

TS_CONFIG: ColumnClause[Any] = literal_column("'russian'::regconfig")
WORD_SIMILARITY_THRESHOLD = "0.5"
WHOLE_SIMILARITY_WEIGHT = 0.25
FUZZY_CANDIDATES = 500
PROXIMITY_WEIGHT = 0.5
PROXIMITY_SCALE_M = 5000.0
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
    fuzzy_rank: ColumnElement[float]
    """Trigram scores cost ~10x a text-search rank per row: fuzzy stage only."""


def text_match(
    query: str,
    tsv: Expression,
    text: Expression,
    fuzzy_text: Expression | None = None,
) -> TextMatch | None:
    """``fuzzy_text`` feeds the typo filter's index, ``text`` ranks the survivors."""
    tokens = tokenize(query)
    if not tokens:
        return None
    prefix = _tsquery(tokens, ":*")
    exact = case((tsv.op("@@")(_tsquery(tokens)), 1.0), else_=0.0)
    rank = exact + func.ts_rank(tsv, prefix, 2)
    fuzzy_rank = func.word_similarity(query, text) + (
        WHOLE_SIMILARITY_WEIGHT * func.similarity(query, text)
    )
    return TextMatch(
        morphological=tsv.op("@@")(prefix),
        fuzzy=literal(query, String).op("<%")(
            text if fuzzy_text is None else fuzzy_text
        ),
        rank=rank,
        fuzzy_rank=fuzzy_rank,
    )


def point_element(point: PointDTO) -> WKTElement:
    return WKTElement(f"POINT({point.lon} {point.lat})", srid=4326)


def distance_m(spot: Expression, near: PointDTO) -> ColumnElement[Any]:
    return func.ST_DistanceSphere(spot, point_element(near), type_=Float)


def proximity(spot: Expression, near: PointDTO) -> ColumnElement[Any]:
    """Up to ``PROXIMITY_WEIGHT``, halved at ``PROXIMITY_SCALE_M`` from ``near``."""
    return func.coalesce(
        PROXIMITY_WEIGHT / (1 + distance_m(spot, near) / PROXIMITY_SCALE_M),
        0.0,
        type_=Float,
    )


async def _use_word_similarity_threshold(repo: SQLAlchemyRepository[Any]) -> None:
    await repo.execute(
        select(
            func.set_config(
                "pg_trgm.word_similarity_threshold",
                WORD_SIMILARITY_THRESHOLD,
                True,
            )
        )
    )


async def search_ranked(
    repo: SQLAlchemyRepository[Any],
    build: Callable[[ColumnElement[bool]], Select[Any]],
    match: TextMatch,
    limit: int,
    *,
    tie_break: Sequence[Expression] = (),
    options: Sequence[ExecutableOption] | None = None,
    near: PointDTO | None = None,
    spot: Expression | None = None,
    key: Expression,
) -> list[tuple[Any, float]]:
    """Top ``limit`` with scores; the fuzzy stage ranks ``FUZZY_CANDIDATES`` at most."""
    await _use_word_similarity_threshold(repo)
    for predicate, rank, capped in (
        (match.morphological, match.rank, False),
        (match.fuzzy, match.fuzzy_rank, True),
    ):
        score = rank
        if near is not None and spot is not None:
            score = score + proximity(spot, near)
        base = build(predicate)
        if capped:
            candidates = base.with_only_columns(key).limit(FUZZY_CANDIDATES)
            base = base.where(key.in_(candidates))
        stmt = (
            base.add_columns(score.label("score"))
            .order_by(score.desc(), *tie_break)
            .limit(limit)
        )
        if options:
            stmt = stmt.options(*options)
        rows = (await repo.execute(stmt)).unique().all()
        if rows:
            return [(row[0], float(row[1])) for row in rows]
    return []


async def search_page(
    repo: SQLAlchemyRepository[Any],
    build: Callable[[ColumnElement[bool]], Select[Any]],
    match: TextMatch,
    pagination: PageParams,
    *,
    tie_break: Sequence[Expression] = (),
    options: Sequence[ExecutableOption] | None = None,
) -> tuple[Any, int]:
    """Stemmed prefix match first; trigram similarity (typo tolerance) only
    when that finds nothing, so exact-ish queries aren't diluted by fuzzy
    hits."""
    await _use_word_similarity_threshold(repo)
    for predicate, rank in (
        (match.morphological, match.rank),
        (match.fuzzy, match.fuzzy_rank),
    ):
        base = build(predicate)
        total = (
            await repo.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar_one()
        if not total:
            continue
        stmt = (
            base.order_by(rank.desc(), *tie_break)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        if options:
            stmt = stmt.options(*options)
        return (await repo.execute(stmt)).unique().scalars(), total
    return [], 0
