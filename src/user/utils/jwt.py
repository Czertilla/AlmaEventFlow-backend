from uuid import UUID
from fastapi_users.authentication import JWTStrategy as Base
from fastapi_users.jwt import generate_jwt
from fastapi_users.models import UP


class JwtStrategy(Base):
    async def write_token(self, user: UP):
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
