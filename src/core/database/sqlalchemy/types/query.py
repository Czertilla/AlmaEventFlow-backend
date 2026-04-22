from core.config.settings import settings, DBManagerType


if settings.DB_DBMS == DBManagerType.postgres:
    from sqlalchemy.dialects.postgresql import insert
elif settings.DB_DBMS == DBManagerType.sqlite:
    from sqlalchemy.dialects.sqlite import insert

__all__ = ["insert"]