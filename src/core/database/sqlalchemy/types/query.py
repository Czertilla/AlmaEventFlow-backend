from core.config.settings import DBManagerType, settings

if DBManagerType.postgres == settings.DB_DBMS:
    from sqlalchemy.dialects.postgresql import insert
elif DBManagerType.sqlite == settings.DB_DBMS:
    from sqlalchemy.dialects.sqlite import insert

__all__ = ["insert"]