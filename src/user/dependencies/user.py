from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from core.config.settings import settings
from core.database.sqlalchemy.session import get_engine, get_url
from core.dependencies.session import get_session_maker
from user.repositories.user import UserRepo
from user.services.user import UserService
from user.uow.user import UserUOW
from user.utils.password import PasswordHelper

if settings.MONOLITH:

    def get_session_maker() -> async_sessionmaker:
        return async_sessionmaker(
            get_engine(get_url(db_name="user")), expire_on_commit=True
        )


async def get_async_session(
    sessionmaker: async_sessionmaker = Depends(get_session_maker),
) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker() as session:
        yield session


async def get_user_repo(session: AsyncSession = Depends(get_async_session)):
    yield UserRepo(session)


def get_user_uow(sessionmaker: async_sessionmaker = Depends(get_session_maker)):
    return UserUOW(sessionmaker)


def get_password_helper():
    return PasswordHelper()


def get_user_service(
    user_uow=Depends(get_user_uow), password_helper=Depends(get_password_helper)
):
    return UserService(user_uow, password_helper=password_helper)
