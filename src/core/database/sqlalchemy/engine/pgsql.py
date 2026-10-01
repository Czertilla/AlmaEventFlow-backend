from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from core.config.settings import Settings

settings = Settings()


def get_url(
    user: str = settings.DB_USER,
    password: str = settings.DB_PASS,
    host: str = settings.DB_HOST,
    port: str = settings.DB_PORT,
    db_name: str = settings.DB_NAME,
) -> str:
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"


def get_engine(db_url: str = get_url()) -> AsyncEngine:
    connect_args = {} if settings.DB_SSL is None else {"ssl": settings.DB_SSL}
    return create_async_engine(db_url, connect_args=connect_args)


engine = get_engine()
