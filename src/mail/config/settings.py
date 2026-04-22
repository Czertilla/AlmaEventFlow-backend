from pydantic import Field, Secret, EmailStr, HttpUrl

from core.config.settings import getSettings, Settings


class MailSettings(Settings):
    """_description_"""

    MAIL_ADMIN_EMAIL: EmailStr = Field(
        default_factory=lambda d: d.get("ADMIN_EMAIL", None)
    )
    """_description_"""

    MAIL_ADMIN_USERNAME: str
    """_description_"""

    MAIL_ADMIN_PASSWORD: Secret[str]
    """_description_"""

    MAIL_HOST: str = "smtp.google.com"
    """_description_"""

    MAIL_PORT: int = 465
    """_description_"""


settings: MailSettings = getSettings(MailSettings)
