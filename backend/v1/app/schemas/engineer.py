from datetime import datetime

from pydantic import BaseModel, Field

from app.models import IncidentCategory
from app.schemas.common import ORMModel

class EngineerCreate(BaseModel):
    user_id: int  # must be a user with the Engineer role
    display_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    specialty: IncidentCategory | None = None
    is_available: bool = True
    max_open_tickets: int = Field(default=10, ge=1)

class EngineerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    specialty: IncidentCategory | None = None
    is_available: bool | None = None
    max_open_tickets: int | None = Field(default=None, ge=1)

class EngineerRead(ORMModel):
    id: int
    user_id: int
    display_name: str
    phone: str | None
    specialty: IncidentCategory | None
    is_available: bool
    max_open_tickets: int
    facility_id: int | None  # from the linked user account
    created_at: datetime
