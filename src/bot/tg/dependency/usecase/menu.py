from typing import Annotated

from aiogram.fsm.context import FSMContext

from bot.tg.dependency.user import UpdatedUserDep
from bot.tg.usecase.menu import MenuUseCase as UseCase

from ._builder import usecase_dep

MenuUseCaseDep = Annotated[(t := UseCase), usecase_dep(t)]
MenuStateUseCaseDep = Annotated[
    (t := UseCase), usecase_dep(t, state=FSMContext)
]
MenuUserUseCaseDep = Annotated[
    (t := UseCase), usecase_dep(t, user=UpdatedUserDep)
]
MenuStateUserUseCaseDep = Annotated[
    (t := UseCase), usecase_dep(t, state=FSMContext, user=UpdatedUserDep)
]
