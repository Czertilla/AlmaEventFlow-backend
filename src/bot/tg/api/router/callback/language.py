from typing import Annotated

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.enum.locales import Locale
from bot.tg.dependency.callback_data import Parse
from bot.tg.dependency.uow import UserUOWDep
from bot.tg.dependency.usecase.menu import MenuStateUserUseCaseDep
from bot.tg.enum.callbacks import CBPrefix
from bot.tg.schema.user import TGUser
from bot.tg.service.user import TelegramUserService
from bot.tg.text.builder.builder import TextBuilder
from bot.tg.usecase.menu import MenuUseCase

router = Router(name="language/")
router.callback_query.filter(F.message.chat.type == "private")


@router.callback_query(F.data == CBPrefix.language)
async def language(callback: CallbackQuery, usecase: MenuStateUserUseCaseDep):
    await callback.message.edit_text(**await usecase.language())


@router.callback_query(F.data.startswith(CBPrefix.language))
async def language_change(
    callback: CallbackQuery,
    data: Annotated[
        Locale | None,
        Parse(
            lambda data: (
                Locale(loc) if (loc := data.split("/")[-1]) != "sys" else None
            )
        ),
    ],
    user: TGUser,
    uow: UserUOWDep,
    state: FSMContext,
):
    if (
        data
        and user._is_lang_modified
        and data.value == user.language_code
        or not data
        and not user._is_lang_modified
    ):
        return
    user = await TelegramUserService(uow).set_lang(
        user,
        data.value if data else callback.from_user.language_code,
        data is None,
    )
    await callback.message.edit_text(
        **await MenuUseCase(
            TextBuilder(lang=user.language_code), user=user, state=state
        ).language()
    )
