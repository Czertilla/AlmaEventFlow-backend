from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import jwt
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.dependencies.sqlalchemy import UOWDep
from core.schema.user import UserJWT

Maker = async_sessionmaker[AsyncSession]


@contextmanager
def bound_sessionmaker(sessionmaker: Maker) -> Generator[None]:
    original: Any = vars(UOWDep)["__call__"]

    def make(self: UOWDep, sessionmaker_: Any = None) -> Any:
        factory: Any = self.uow_cls
        return factory(sessionmaker)

    UOWDep.__call__ = make  # pyright: ignore[reportAttributeAccessIssue]
    try:
        yield
    finally:
        UOWDep.__call__ = original  # pyright: ignore[reportAttributeAccessIssue]


def mint_token(user: UserJWT) -> str:
    from core.utils.jwt import create_jwt_auth

    auth = create_jwt_auth(superuser=True)
    key: str = auth.secret
    if auth.algorithm == "RS256":
        from user.utils.rsa import get_private_key_pem

        key = get_private_key_pem()
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "aud": auth.token_audience,
        "per": str(user.person_id) if user.person_id else None,
        "act": user.is_active,
        "ver": user.is_verified,
        "sup": user.is_superuser,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, key, algorithm=auth.algorithm)


def principal(
    *,
    person_id: UUID | None = None,
    superuser: bool = False,
    verified: bool = True,
    active: bool = True,
) -> dict[str, str]:
    user = UserJWT(
        id=uuid4(),
        person_id=person_id,
        is_active=active,
        is_verified=verified,
        is_superuser=superuser,
    )
    return {"Authorization": f"Bearer {mint_token(user)}"}


@asynccontextmanager
async def api_client(
    app: FastAPI, sessionmaker: Maker
) -> AsyncGenerator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    with bound_sessionmaker(sessionmaker):
        async with httpx.AsyncClient(
            transport=transport, base_url="https://test"
        ) as client:
            yield client
