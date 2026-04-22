from pydantic import Secret

from core.config.settings import getSettings, Settings


class UserSettings(Settings):
    AUTH_BACKEND_NAME: str = "jwt"

    OAUTH_GOOGLE_CLIENT_ID: str
    OAUTH_GOOGLE_CLIENT_SECRET: Secret[str]
    OAUTH_STATE_SECRET: Secret[str] = "SECRET"



settings: UserSettings = getSettings(UserSettings)
