from typing import Annotated

from aiogram.types import User
from aiogram3_di import Depends

from bot.tg.dependency.user import UpdatedUserDep
from bot.tg.text.builder.builder import TextBuilder


def get_text_builder(
    event_from_user: User, user: UpdatedUserDep
) -> TextBuilder:
    if user:
        lang = user.language_code
    elif event_from_user:
        lang = event_from_user.language_code
    else:
        lang = None
    return TextBuilder(lang=lang)


TextBuilderDep = Annotated[TextBuilder, Depends(get_text_builder)]
