from functools import lru_cache
from logging import getLogger
from pydantic import (
    Secret,
    ValidationInfo,
    field_validator,
    Field,
    EmailStr,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from os import environ

from dotenv import load_dotenv

from core.enum.config import DBManagerType
from core.utils.get_version import get_version

load_dotenv()

logger = getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings class.

    This class loads settings from environment variables and the .env file.
    It is used to manage application configuration parameters.
    """

    MONOLITH: bool = False

    IN_MEMORY_BROKER: bool = False

    ADMIN_EMAIL: EmailStr | None = None

    APP_NAME: str = "Simple App"
    """Name of the FastAPI application that will be displayed in places such as Swagger."""

    APP_HOST: str
    """Host of the application that will be displayed in places such as Swagger."""

    FRONTEND_URL: str = "https://aef.czertilla.ru"
    """Base URL of the user-facing frontend. Used to build event page links
    (e.g. in ICS calendar feeds: ``{FRONTEND_URL}/events/{event_id}``)."""

    DB_DBMS: DBManagerType = DBManagerType.__default__
    """Type of database management system used (e.g., sqlite, postgres)."""

    DB_NAME: str = "simple-app"
    """Name of the database used."""

    DB_USER: str | None = None
    """Username for connecting to the database (required for PostgreSQL)."""

    DB_PASS: str | None = None
    """Password for the database user (required for PostgreSQL)."""

    DB_HOST: str | None = None
    """Hostname or IP address of the database server (required for PostgreSQL)."""

    DB_PORT: str | None = None
    """Port number on which the database server is running (required for PostgreSQL)."""

    S3_URL: str = "https://s3.twcstorage.ru"

    S3_BUCKET_NAME: str

    S3_ACCESS_KEY: Secret[str]

    S3_SECRET_KEY: Secret[str]

    MONGO_URL: str = "mongodb://mongo:27017"
    """MongoDB connection URL for Docker containers."""

    REDIS_URL: str = "redis://localhost:6379"
    """URL for connecting to the Redis server (required for Redis)."""

    KAFKA_HOST: str = "localhost"
    """Hostname or IP address of the Kafka server."""

    KAFKA_PORT: str = "9092"
    """Port number on which the Kafka server is running."""

    PASS_SECRET: Secret[str] = "SECRET"
    USER_SECRET: Secret[str] = "SECRET"

    AUTH_COOKIE_MAX_AGE: int = 3600
    AUTH_COOKIE_NAME: str = "auth"

    ACCESS_TOKEN_EXPIRE_SECONDS: int = 900
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 604800

    REFRESH_COOKIE_NAME: str = "refresh"
    AUTH_COOKIE_DOMAIN: str | None = None
    AUTH_COOKIE_SAMESITE: str = "strict"
    AUTH_COOKIE_SECURE: bool = True

    RSA_PRIVATE_KEY_PATH: str = "rsa_private.pem"
    RSA_PUBLIC_KEY_PATH: str = "rsa_public.pem"

    INVITE_TOKEN_LIFETIME: int = 604800

    MAX_PAGE_SIZE: int = 100
    """Maximum number of items to be displayed on a single page. Default is 100."""

    BOT_TG_TOKEN: str | None = None

    DEV_ID_LIST: list[int] = [715648962]

    VERSION: str = Field(default_factory=get_version)
    """The version of this project, displays in messages and descripions"""

    model_config = SettingsConfigDict(env_file=environ, extra="ignore")
    """Configuration for Pydantic settings, defining how environment variables are loaded."""

    @field_validator("DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", mode="before")
    @classmethod
    def check_postgres_fields(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        """
        Ensures that PostgreSQL-related fields are set when DB_DBMS is 'postgres'.

        Raises:
            ValueError: If a required PostgreSQL field is missing.
        """
        if info.data.get("DB_DBMS") == DBManagerType.postgres and not value:
            raise ValueError(
                f"{info.field_name} is required when DB_DBMS is set to 'postgres'"
            )
        return value


@lru_cache
def getSettings[T](settings_class: type[T] = Settings) -> T:
    """
    Returns a cached instance of the application settings.

    This function ensures that the settings are only loaded once and then reused.

    Returns:
        Settings: The application settings instance.
    """
    setting = settings_class()
    return setting


settings: Settings = getSettings()
