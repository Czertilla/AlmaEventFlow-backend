from typing import Any, cast
from httpx_oauth.clients.google import GoogleOAuth2 as Base
from httpx_oauth.exceptions import GetIdEmailError, GetProfileError

from user.config.settings import settings

PROFILE_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleOAuth2(Base):
    async def get_profile(self, token: str) -> dict[str, Any]:
        async with self.get_httpx_client() as client:
            response = await client.get(
                PROFILE_ENDPOINT,
                params={"personFields": "emailAddresses,names"},
                headers={
                    **self.request_headers,
                    "Authorization": f"Bearer {token}",
                },
            )

            if response.status_code >= 400:
                raise GetProfileError(response=response)

            return cast(dict[str, Any], response.json())
        
    async def get_id_email(self, token: str) -> tuple[str, str | None]:
        try:
            profile = await self.get_profile(token)
        except GetProfileError as e:
            raise GetIdEmailError(response=e.response) from e

        user_id = profile["sub"]
        user_email = profile["email"]
        username = profile.get("name", None)

        return user_id, (user_email, username)


google_oauth_client = GoogleOAuth2(
    settings.OAUTH_GOOGLE_CLIENT_ID,
    settings.OAUTH_GOOGLE_CLIENT_SECRET.get_secret_value(),
)
