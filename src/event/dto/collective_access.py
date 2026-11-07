from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectivePrincipalDTO:
    is_principal: bool
    name: str | None = None
    is_verified: bool = False
