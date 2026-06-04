from uuid import UUID
from fastapi_users.authentication import JWTStrategy as Base
from fastapi_users.jwt import generate_jwt
from fastapi_users.models import UP

from user.utils.rsa import get_private_key_pem, get_public_key_pem


class AccessStrategy(Base):
    def __init__(
        self,
        secret: str | None = None,
        lifetime_seconds: int | None = None,
        token_audience: list[str] | None = None,
        algorithm: str = "RS256",
        public_key: str | None = None,
    ):
        super().__init__(
            secret=secret or get_private_key_pem(),
            lifetime_seconds=lifetime_seconds,
            token_audience=token_audience or ["fastapi-users:auth"],
            algorithm=algorithm,
            public_key=public_key or get_public_key_pem(),
        )

    async def write_token(self, user: UP) -> str:
        data = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "per": str(p_id)
            if isinstance(p_id := getattr(user, "person_id"), UUID)
            else None,
            "act": user.is_active,
            "ver": user.is_verified,
            "sup": user.is_superuser,
        }
        return generate_jwt(
            data,
            self.encode_key,
            self.lifetime_seconds,
            algorithm=self.algorithm,
        )
