class InvalidLinkTokenException(Exception):  # noqa: N818  # same *Exception naming as the other services
    """Telegram account-link token failed signature/audience validation."""


class LinkTokenExpiredException(Exception):  # noqa: N818  # same *Exception naming as the other services
    """Telegram account-link token has expired."""
