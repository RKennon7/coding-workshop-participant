from pydantic import BaseModel, Field, field_validator, model_validator

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


# ---------- bulk setup: POST /facilities/setup and POST /facilities/{id}/buildings/bulk ----------
# floors are named "Floor 1".."Floor N", seats "{code}-{floor}-{seat:02d}" (e.g. NT-3-02)

MAX_SEATS_PER_REQUEST = 5000

class BuildingPlan(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z0-9]+$", description="seat code prefix, e.g. NT")
    floors: int = Field(ge=1, le=100)
    seats_per_floor: int = Field(ge=0, le=200)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("code")
    @classmethod
    def _upper_code(cls, value: str) -> str:
        return value.upper()

class BuildingsBulkCreate(BaseModel):
    buildings: list[BuildingPlan] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _check_plan(self) -> "BuildingsBulkCreate":
        for label, values in (("name", [b.name.lower() for b in self.buildings]), ("code", [b.code for b in self.buildings])):
            if len(set(values)) != len(values):
                raise ValueError(f"each building needs a different {label}")
        seats = sum(b.floors * b.seats_per_floor for b in self.buildings)
        if seats > MAX_SEATS_PER_REQUEST:
            raise ValueError(f"that's {seats} seats, at most {MAX_SEATS_PER_REQUEST} can be created at once")
        return self

class FacilitySetup(BuildingsBulkCreate):
    name: str = Field(min_length=1, max_length=100)
    address: str | None = None

class FacilitySetupResult(BaseModel):
    facility: FacilityRead
    buildings: int
    floors: int
    seats: int


# GET /<location>/{id}/delete-impact: what deleting it would remove, shown in the confirm dialog
class DeleteImpact(BaseModel):
    buildings: int
    floors: int
    seats: int
    incidents: int  # > 0 means the delete is refused: deactivate instead so ticket history is kept
    users: int      # facility only: users left without a facility until they're reassigned
