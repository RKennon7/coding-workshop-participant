"""Request/response schemas for incidents, their status history and notes (routers/incidents.py)."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import IncidentCategory, IncidentPriority, IncidentStatus
from app.schemas.common import ORMModel, UserSummary

class IncidentCreate(BaseModel):
    """Body for reporting a new incident. Any role may report.

    No status/assignee fields: a new ticket always starts Open and unassigned, reported by the caller.
    The router checks that floor/seat belong to the building and, for non-admins, that the building
    is on their own campus.
    """
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: IncidentCategory
    priority: IncidentPriority = IncidentPriority.MEDIUM
    building_id: int
    floor_id: int | None = None
    seat_id: int | None = None

# every editable field. which ones a caller may actually send depends on their role (see routers/incidents.py)
class IncidentUpdate(BaseModel):
    """PATCH body. Only the fields sent are applied; sending a field your role may not change is a 403.

    blocked_reason is required when moving to Blocked and escalation_reason when setting is_escalated
    (400 otherwise); both are cleared automatically once they no longer apply.
    """
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
    """An incident as returned by the API, with reporter/assignee embedded as UserSummary.

    Location is returned as ids only; the frontend resolves names from the facilities endpoints.
    """
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
    """One audit-trail entry. from_status is null for the "created as Open" row."""
    id: int
    from_status: IncidentStatus | None
    to_status: IncidentStatus
    reason: str | None
    changed_by: UserSummary
    changed_at: datetime


class NoteCreate(BaseModel):
    """Body for adding a note to an incident."""
    body: str = Field(min_length=1)
    is_internal: bool = False  # engineers/admins only

class NoteUpdate(BaseModel):
    """PATCH body for editing a note. Only the note's author may edit it; is_internal=True is engineers/admins only."""
    body: str | None = Field(default=None, min_length=1)
    is_internal: bool | None = None

class NoteRead(ORMModel):
    """A note as returned by the API. Employees never receive internal notes."""
    id: int
    incident_id: int
    author_id: int
    author: UserSummary
    body: str
    is_internal: bool
    created_at: datetime
    updated_at: datetime
