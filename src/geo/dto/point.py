from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PointDTO:
    lat: float
    lon: float
