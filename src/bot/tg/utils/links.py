from uuid import UUID

from core.config.settings import settings


def site_url(path: str = "") -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def login_url() -> str:
    return site_url("/auth/login")


def register_url() -> str:
    return site_url("/auth/register")


def profile_url() -> str:
    return site_url("/profile")


def event_url(event_id: UUID | str) -> str:
    return site_url(f"/event/{event_id}")
