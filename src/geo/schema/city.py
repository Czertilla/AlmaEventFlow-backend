from pydantic import BaseModel

class CityCreate(BaseModel):
    name: str
    

class CityCascadeCreate(BaseModel):
    name: str
    region: str
    country: str
