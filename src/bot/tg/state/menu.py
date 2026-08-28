from bot.tg.utils.state.point import PointedStatesGroup


class MenuStateGroup(PointedStatesGroup):
    class Help(PointedStatesGroup): ...

    class Account(PointedStatesGroup): ...

    class Settings(PointedStatesGroup):
        class Language(PointedStatesGroup): ...
