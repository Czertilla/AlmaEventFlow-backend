from typing import Self

from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, ReplyParameters

from bot.tg.keyboard.inline import InlineBuilder
from bot.tg.schema.user import TGUser
from bot.tg.text.builder import TextBuilder
from core.uow.abc import ABCUnitOfWork
from core.utils.requirer import required_field


class BotUseCase:
    """
    Abstract base class for bot use cases.

    Attributes:
        text_builder (TextBuilder): The message builder for
            formatting texts.
        user (TGUser | None): The user for whom the bot is being built.
    """

    required_message = required_field("message")
    required_user = required_field("user")
    required_state = required_field("state")
    required_uow = required_field("uow")
    required_bot = required_field("bot")

    def __init__(
        self,
        text_builder: TextBuilder,
        *,
        user: TGUser | None = None,
        bot: Bot | None = None,
        dp: Dispatcher | None = None,
        uow: ABCUnitOfWork | None = None,
        state: FSMContext | None = None,
        message: Message | None = None,
    ):
        """
        Initialize the BotUseCase.

        Args:
            text_builder (TextBuilder): The message builder instance
                used to generate message texts.
            user (TGUser): The user for whom the bot actions are performed.
        """
        super().__init__(text_builder)
        self.state = state
        self.text_builder = text_builder
        self.message = message
        self.user = user
        self.dp = dp
        self.uow = uow
        self.bot = bot

    @required_state
    async def edit_state(
        self: Self, state: State, clear: bool = False, **data: dict
    ) -> None:
        """
        Edit the state and update the data.

        Args:
            state (StatesGroup): The state to set.
            **data (dict): The data to update.

        Requires:
            - state (FSMContext): The state to set.
            - **data (dict): The data to update.
        """
        self.state: FSMContext
        clear and await self.state.clear()
        await self.state.set_state(state)
        await self.state.update_data(**data)

    @required_message
    def get_reply_params(self) -> ReplyParameters:
        return ReplyParameters(message_id=self.message.message_id)


class InlineBuilderMixin:
    text_builder: TextBuilder

    def __init__(self, text_builder: TextBuilder, *args, **kwargs):
        super().__init__()
        self.inline_builder = InlineBuilder(text_builder)
