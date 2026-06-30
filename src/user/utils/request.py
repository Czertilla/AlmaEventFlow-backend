from logging import getLogger

from fastapi import Request

logger = getLogger(__name__)

MAX_IP_LENGTH = 45
"""Fits the longest textual IPv6 form (incl. IPv4-mapped) — matches the
``session.ip_address`` column width."""


def extract_device_info(request: Request | None) -> str | None:
    """User agent of the requesting client, used as a human-readable device
    label in the session manager."""
    if request is None:
        return None
    return request.headers.get("user-agent")


def extract_ip(request: Request | None) -> str | None:
    """Best-effort client IP. Honors the left-most ``X-Forwarded-For`` hop when
    behind a proxy, otherwise the direct peer. The result is truncated to the
    stored column width so an oversized/spoofed header can never overflow it."""
    if request is None:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        return None
    return ip[:MAX_IP_LENGTH] if ip else None
