from pydantic import BaseModel, ConfigDict


class CityCreate(BaseModel):
    name: str


class CityCascadeCreate(BaseModel):
    name: str
    region: str
    country: str


class CityRead(BaseModel):
    id: int
    region_id: int
    name: str
    acronym: str | None = None

    model_config = ConfigDict(from_attributes=True)
