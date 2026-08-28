from typing import Annotated

from aiogram.fsm.context import FSMContext

from bot.tg.dependency.user import UpdatedUserDep
from bot.tg.usecase.account import AccountUseCase as UseCase

from ._builder import usecase_dep

AccountStateUserUseCaseDep = Annotated[
    (t := UseCase), usecase_dep(t, state=FSMContext, user=UpdatedUserDep)
]
