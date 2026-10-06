from typing import Annotated

from bot.tg.usecase.leader import LeaderUseCase as UseCase

from ._builder import usecase_dep

LeaderUseCaseDep = Annotated[(t := UseCase), usecase_dep(t)]
