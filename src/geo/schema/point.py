from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from geoalchemy2.elements import WKTElement, WKBElement
from geoalchemy2.shape import to_shape


class Point(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def from_geoalchemy(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        if isinstance(data, WKTElement):
            wkt = (data.data or "").strip()

            if wkt.upper().startswith("SRID="):
                _, wkt = wkt.split(";", 1)
                wkt = wkt.strip()

            if not wkt.upper().startswith("POINT"):
                raise ValueError(f"Expected POINT WKT, got: {wkt!r}")

            geom = to_shape(data)
            return {"lon": float(geom.x), "lat": float(geom.y)}

        if isinstance(data, WKBElement):
            geom = to_shape(data)
            if geom.geom_type != "Point":
                raise ValueError(f"Expected Point WKB, got: {geom.geom_type}")
            return {"lon": float(geom.x), "lat": float(geom.y)}

        return data
