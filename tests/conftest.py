import asyncio
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

os.environ.setdefault("DB_DBMS", "postgres")
os.environ.setdefault("MONOLITH", "true")
os.environ.setdefault("APP_ARCHITECTURE", "monolith")
os.environ.setdefault("IN_MEMORY_BROKER", "true")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("APP_HOST", "localhost")
os.environ.setdefault("S3_BUCKET_NAME", "test")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

COMPOSE_FILE = ROOT / "docker-compose.test.yml"
SERVICE_DATABASES = ("user", "profile", "org", "event", "geo", "notify")
GEO_EXTENSIONS = ("postgis", "postgis_topology", "pg_trgm")
MIGRATE_MODULES = os.environ.get(
    "TEST_MIGRATE_MODULES", ",".join(SERVICE_DATABASES)
).split(",")


def _compose(*args: str) -> None:
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        check=True,
        cwd=ROOT,
    )


async def _connect(database: str):
    import asyncpg

    return await asyncpg.connect(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=database,
    )


async def _provision_databases() -> None:
    """Creates each service database (CREATE DATABASE cannot run in a tx, so it
    is done outside Alembic) and the PostGIS extensions the geo schema needs."""
    admin = await _connect("postgres")
    try:
        for name in SERVICE_DATABASES:
            exists = await admin.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", name
            )
            if not exists:
                await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()

    geo = await _connect("geo")
    try:
        for extension in GEO_EXTENSIONS:
            await geo.execute(f"CREATE EXTENSION IF NOT EXISTS {extension}")
    finally:
        await geo.close()


def _run_migrations() -> None:
    for module in MIGRATE_MODULES:
        subprocess.run(
            [sys.executable, "-m", "alembic", "-n", module, "upgrade", "head"],
            check=True,
            cwd=ROOT,
            env=os.environ.copy(),
        )


@pytest.fixture(scope="session")
def test_database():
    """Spins up the dockerized test Postgres, provisions per-service databases
    and runs every module's migrations to head, once per session. Requires a
    running Docker engine. Set ``TEST_DB_KEEP=0`` to tear the container down
    afterwards (default keeps it for fast reruns)."""
    _compose("up", "-d", "--wait")
    try:
        asyncio.run(_provision_databases())
        _run_migrations()
        yield
    finally:
        if os.environ.get("TEST_DB_KEEP", "1") != "1":
            _compose("down", "-v")
