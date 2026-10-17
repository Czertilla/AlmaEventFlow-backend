from urllib.parse import quote
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


MAP_QUERY_LENGTH = 100


def map_url(text: str, lat: float | None, lon: float | None) -> str:
    """Yandex Maps: the point if both coordinates are known, else a search."""
    if lat is not None and lon is not None:
        return f"https://yandex.ru/maps/?pt={lon:.6f},{lat:.6f}&z=17&l=map"
    return f"https://yandex.ru/maps/?text={quote(text[:MAP_QUERY_LENGTH], safe='')}"
