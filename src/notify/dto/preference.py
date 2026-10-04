from dataclasses import dataclass

from core.enum.notify import TransportTypeEnum


@dataclass(frozen=True, slots=True)
class PreferenceItemDTO:
    transport: TransportTypeEnum
    is_enabled: bool


@dataclass(frozen=True, slots=True)
class PreferencesDTO:
    preferences: list[PreferenceItemDTO]


@dataclass(frozen=True, slots=True)
class PreferencesUpdateDTO:
    preferences: list[PreferenceItemDTO]
