from datetime import datetime

from pydantic import BaseModel, Field

from app.models import IncidentCategory, IncidentPriority, IncidentStatus
from app.schemas.common import ORMModel, UserSummary

class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: IncidentCategory
    priority: IncidentPriority = IncidentPriority.MEDIUM
    building_id: int
    floor_id: int | None = None
    seat_id: int | None = None

# every editable field. which ones a caller may actually send depends on their role (see routers/incidents.py)
class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    category: IncidentCategory | None = None
    priority: IncidentPriority | None = None
    status: IncidentStatus | None = None
    blocked_reason: str | None = None
    is_escalated: bool | None = None
    escalation_reason: str | None = None
    assignee_id: int | None = None
    building_id: int | None = None
    floor_id: int | None = None
    seat_id: int | None = None

class IncidentRead(ORMModel):
    id: int
    title: str
    description: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus
    blocked_reason: str | None
    is_escalated: bool
    escalation_reason: str | None
    reporter_id: int
    assignee_id: int | None
    reporter: UserSummary
    assignee: UserSummary | None
    building_id: int
    floor_id: int | None
    seat_id: int | None
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None
    assigned_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None

class StatusHistoryRead(ORMModel):
    id: int
    from_status: IncidentStatus | None
    to_status: IncidentStatus
    reason: str | None
    changed_by: UserSummary
    changed_at: datetime


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False  # engineers/admins only

class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1)
    is_internal: bool | None = None

class NoteRead(ORMModel):
    id: int
    incident_id: int
    author_id: int
    author: UserSummary
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime
