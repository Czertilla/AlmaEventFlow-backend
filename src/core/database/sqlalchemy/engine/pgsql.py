from core.config.settings import Settings
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

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
    return create_async_engine(db_url)


engine = get_engine()
