from typing import TypedDict

from aiogram.types import (
    DateTimeUnion,
    InlineQueryResultsButton,
    InlineQueryResultUnion,
    InputFile,
    InputFileUnion,
    LinkPreviewOptions,
    MediaUnion,
    MessageEntity,
    ReplyMarkupUnion,
    ReplyParameters,
    SuggestedPostParameters,
)


class MessageArgs(TypedDict, total=False):
    text: str
    business_connection_id: str | None
    message_thread_id: int | None
    parse_mode: str | None
    entities: list[MessageEntity] | None
    link_preview_options: LinkPreviewOptions | None
    disable_notification: bool | None
    protect_content: bool | None
    allow_paid_broadcast: bool | None
    message_effect_id: str | None
    message_id: int | None
    reply_parameters: ReplyParameters | None
    reply_markup: ReplyMarkupUnion | None
    allow_sending_without_reply: bool | None
    disable_web_page_preview: bool | None
    reply_to_message_id: int | None


class CallbackAnswerArgs(TypedDict):
    text: str | None = None
    show_alert: bool | None = None
    url: str | None = None
    cache_time: int | None = None


class MediaGroupArgs(TypedDict, total=False):
    media: list[MediaUnion]
    direct_messages_topic_id: int | None
    disable_notification: bool
    protect_content: bool | None
    allow_paid_broadcast: bool | None
    message_effect_id: str | None
    reply_parameters: ReplyParameters | None
    allow_sending_without_reply: bool | None
    reply_to_message_id: int | None


class EditMediaArgs(TypedDict, total=False):
    ...


class PhotoArgs(TypedDict, total=False):
    photo: InputFileUnion
    direct_messages_topic_id: int | None
    caption: str | None
    parse_mode: str | None
    caption_entities: list[MessageEntity] | None
    show_caption_above_media: bool | None
    has_spoiler: bool | None
    disable_notification: bool | None
    protect_content: bool | None
    allow_paid_broadcast: bool | None
    message_effect_id: str | None
    suggested_post_parameters: SuggestedPostParameters | None
    reply_parameters: ReplyParameters | None
    reply_markup: ReplyMarkupUnion | None
    allow_sending_without_reply: bool | None
    reply_to_message_id: int | None


class VideoArgs(TypedDict, total=False):
    video: InputFileUnion
    direct_messages_topic_id: int
    duration: int
    width: int
    height: int
    thumbnail: InputFile
    cover: InputFileUnion
    start_timestamp: DateTimeUnion
    caption: str
    parse_mode: str
    caption_entities: list[MessageEntity] | None
    show_caption_above_media: bool
    has_spoiler: bool
    supports_streaming: bool | None
    disable_notification: bool
    protect_content: bool
    allow_paid_broadcast: bool
    message_effect_id: str
    suggested_post_parameters: SuggestedPostParameters
    reply_parameters: ReplyParameters
    reply_markup: ReplyMarkupUnion
    allow_sending_without_reply: bool
    reply_to_message_id: int


class InlineResult(TypedDict, total=False):
    results: list[InlineQueryResultUnion]
    cache_time: int | None
    is_personal: bool | None
    next_offset: str | None
    button: InlineQueryResultsButton | None
    switch_pm_parameter: str | None
    switch_pm_text: str | None
