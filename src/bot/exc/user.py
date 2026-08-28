class InvalidLinkTokenException(Exception):
    """Telegram account-link token failed signature/audience validation."""


class LinkTokenExpiredException(Exception):
    """Telegram account-link token has expired."""
