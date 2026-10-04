from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config.settings import settings
from core.database.sqlalchemy.session import get_engine, get_url
from core.dependencies.session import get_session_maker
from user.api.manager import UserManager
from user.repositories.user import UserRepo
from user.service.user import UserService
from user.uow.user import UserUOW
from user.utils.password import PasswordHelper

if settings.MONOLITH:

    def get_session_maker() -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            get_engine(get_url(db_name="user")), expire_on_commit=True
        )


async def get_async_session(
    sessionmaker: async_sessionmaker = Depends(get_session_maker),
) -> AsyncGenerator[AsyncSession]:
    async with sessionmaker() as session:
        yield session


async def get_user_repo(session: AsyncSession = Depends(get_async_session)):
    yield UserRepo(session)


def get_user_uow(
    sessionmaker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
) -> UserUOW:
    return UserUOW(sessionmaker)


def get_password_helper() -> PasswordHelper:
    return PasswordHelper()


def get_user_service(
    user_uow: UserUOW = Depends(get_user_uow),
    password_helper: PasswordHelper = Depends(get_password_helper),
) -> UserService:
    return UserService(user_uow, password_helper=password_helper)


def get_user_manager(
    user_service: UserService = Depends(get_user_service),
) -> UserManager:
    return UserManager(user_service)
