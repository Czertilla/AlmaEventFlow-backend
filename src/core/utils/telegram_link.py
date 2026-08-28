TELEGRAM_LINK_REDIS_PREFIX = "tg-link:"
"""Redis key prefix shared by ``user`` (writer, ``create_telegram_link_token``)
and ``bot`` (reader, ``AccountLinkService``) for the bot deep-link's one-time
code -> person_id mapping. A raw JWT doesn't fit here: Telegram's ``start``
deep-link parameter only allows up to 64 ``[A-Za-z0-9_-]`` characters, far too
short for a signed token, so the actual state lives in Redis instead and the
URL only ever carries a short opaque code."""
