from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelegramLinkTokenDTO:
    token: str
    deep_link: str
    expires_at: int
