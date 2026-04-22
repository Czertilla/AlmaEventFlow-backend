import asyncio
from logging.config import fileConfig
import os

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context, op
import sqlalchemy as sa

import sys

if os.getenv("APP_ARCHITECTURE") in ("monolith", None):
    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")),
    )

from core.config.settings import Settings
from core.database.sqlalchemy.core import Base
from logging import getLogger

logger = getLogger(__name__)

current_service = context.config.get_main_option("database_name")
os.environ["DB_NAME"] = current_service
if current_service == "geo":
    from geoalchemy2 import alembic_helpers

config = context.config
section = config.config_ini_section
settings = Settings()

if settings.DB_DBMS == "sqlite":
    sqlalchemy_url = f"sqlite+aiosqlite:///{settings.DB_NAME}.db"
elif settings.DB_DBMS == "postgres":
    sqlalchemy_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
else:
    raise ValueError(f"Unsupported DB_DBMS: {settings.DB_DBMS}")
config.set_main_option("sqlalchemy.url", sqlalchemy_url)
# config.set_section_option(section, "DB_HOST", settings.DB_HOST)
# config.set_section_option(section, "DB_NAME", settings.DB_NAME)
# config.set_section_option(section, "DB_PASS", settings.DB_PASS)
# config.set_section_option(section, "DB_PORT", settings.DB_PORT)
# config.set_section_option(section, "DB_USER", settings.DB_USER)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

__import__(f"{current_service}.models", fromlist=["*"])

# Комбинируем метаданные из core и сервиса
target_metadata = Base.metadata

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    if not alembic_helpers.include_object(
        object, name, type_, reflected, compare_to
    ) or (type_ == "table" and name in ("layer", "topology")):
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    if current_service == "geo":
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )
    else:
        context.configure(
            url=url,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    if current_service == "geo":
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
            compare_type=True,
            compare_server_default=True,
        )
    else:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    url = config.get_main_option("sqlalchemy.url")

    if current_service == "geo":
        context.configure(
            url=url,
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )
    else:
        context.configure(url=url)

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
