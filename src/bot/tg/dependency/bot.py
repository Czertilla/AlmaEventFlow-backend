from typing import Annotated

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from fastapi import Depends

from core.config.settings import settings


def get_bot_token() -> str:
    return settings.BOT_TG_TOKEN


def get_bot_session() -> AiohttpSession | None:
    if not (proxy := settings.BOT_TG_PROXY):
        return
    return AiohttpSession(proxy=proxy)


def get_bot_default() -> DefaultBotProperties:
    return DefaultBotProperties(parse_mode=settings.BOT_PARSE_MODE)


BotDefaultDep = Annotated[DefaultBotProperties, Depends(get_bot_default)]
BotTokenDep = Annotated[str, Depends(get_bot_token)]
BotSessionDep = Annotated[AiohttpSession, Depends(get_bot_session)]


def bot_factory(
    token: BotTokenDep,
    default: BotDefaultDep,
    session: BotSessionDep,
) -> Bot:
    return Bot(token=token, session=session, default=default)


BotDep = Annotated[Bot, Depends(bot_factory)]

bot = bot_factory(
    token=get_bot_token(), session=get_bot_session(), default=get_bot_default()
)
