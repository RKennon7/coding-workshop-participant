from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

# Facility > Building > Floor > Seat. Each level has Create (POST), Update (PATCH, all optional) and Read schemas.

class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str | None = None
    is_active: bool = True

class FacilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = None
    is_active: bool | None = None

class FacilityRead(ORMModel):
    id: int
    name: str
    address: str | None
    is_active: bool


class BuildingCreate(BaseModel):
    facility_id: int
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

class BuildingUpdate(BaseModel):
    facility_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

class BuildingRead(ORMModel):
    id: int
    facility_id: int
    name: str
    is_active: bool


class FloorCreate(BaseModel):
    building_id: int
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

class FloorUpdate(BaseModel):
    building_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

class FloorRead(ORMModel):
    id: int
    building_id: int
    name: str
    is_active: bool


class SeatCreate(BaseModel):
    floor_id: int
    code: str = Field(min_length=1, max_length=50)
    is_active: bool = True

class SeatUpdate(BaseModel):
    floor_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=50)
    is_active: bool | None = None

class SeatRead(ORMModel):
    id: int
    floor_id: int
    code: str
    is_active: bool
