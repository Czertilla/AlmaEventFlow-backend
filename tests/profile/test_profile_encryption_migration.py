import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

ROOT = Path(__file__).resolve().parents[2]
BEFORE = "e8b2c4d6a913"
PLAIN = {
    "number": "character varying",
    "issued_authority": "character varying",
    "issued_date": "date",
    "expire_date": "date",
}


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-n", "profile", *args],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )


async def _sql(engine: AsyncEngine, sql: str, **params: Any) -> list[Any]:
    async with engine.begin() as conn:
        result = await conn.execute(text(sql), params)
        return list(result.all()) if result.returns_rows else []


async def _types(engine: AsyncEngine) -> dict[str, str]:
    rows = await _sql(
        engine,
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name = 'passport' AND column_name = ANY(:names)",
        names=list(PLAIN),
    )
    return {row.column_name: row.data_type for row in rows}


async def _has_person_key(engine: AsyncEngine) -> bool:
    rows = await _sql(engine, "SELECT to_regclass('person_key') IS NOT NULL AS found")
    return bool(rows[0].found)


async def test_the_migration_guards_the_data_and_rolls_back(
    profile_engine: AsyncEngine,
) -> None:
    person_id, passport_id = uuid4(), uuid4()
    try:
        down = _alembic("downgrade", BEFORE)
        assert down.returncode == 0, down.stderr
        assert await _types(profile_engine) == PLAIN
        assert not await _has_person_key(profile_engine)

        await _sql(
            profile_engine,
            "INSERT INTO person (id, surname, name, created_at) "
            "VALUES (:id, 'Ivanov', 'Ivan', now())",
            id=person_id,
        )
        await _sql(
            profile_engine,
            "INSERT INTO profile (id, created_at) VALUES (:id, now())",
            id=person_id,
        )
        await _sql(
            profile_engine,
            "INSERT INTO passport (id, profile_id, number, expire_date, is_foreign, "
            "created_at) VALUES (:id, :p, '4510 123456', '2030-01-01', false, now())",
            id=passport_id,
            p=person_id,
        )
        refused = _alembic("upgrade", "head")

        assert refused.returncode != 0
        assert "passport has 1 rows with data" in refused.stderr
        assert "Nothing was changed" in refused.stderr
        assert await _types(profile_engine) == PLAIN
        assert not await _has_person_key(profile_engine)
        assert await _sql(
            profile_engine, "SELECT number FROM passport WHERE id = :id", id=passport_id
        ) != []

        await _sql(profile_engine, "DELETE FROM passport")
        up = _alembic("upgrade", "head")

        assert up.returncode == 0, up.stderr
        assert set((await _types(profile_engine)).values()) == {"bytea"}
        assert await _has_person_key(profile_engine)

        await _sql(
            profile_engine,
            "INSERT INTO passport (id, profile_id, number, expire_date, is_foreign, "
            "created_at) "
            "VALUES (:id, :p, '\\x01'::bytea, '\\x01'::bytea, false, now())",
            id=passport_id,
            p=person_id,
        )
        kept = _alembic("downgrade", BEFORE)

        assert kept.returncode != 0
        assert "returning its columns to plain text" in kept.stderr
        assert set((await _types(profile_engine)).values()) == {"bytea"}
    finally:
        await _sql(profile_engine, "DELETE FROM passport")
        await _sql(profile_engine, "DELETE FROM person WHERE id = :id", id=person_id)
        restored = _alembic("upgrade", "head")
        assert restored.returncode == 0, restored.stderr
