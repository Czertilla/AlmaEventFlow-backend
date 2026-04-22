from fastapi_mail import ConnectionConfig, FastMail

from mail.config.settings import settings


defaconf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_ADMIN_USERNAME,
    MAIL_PASSWORD=settings.MAIL_ADMIN_PASSWORD.get_secret_value(),
    MAIL_FROM=settings.MAIL_ADMIN_EMAIL,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_HOST,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


def get_fastmail(conf: ConnectionConfig = defaconf) -> FastMail:
    return FastMail(conf)
