from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.models import IncidentCategory, IncidentPriority, IncidentStatus
from app.schemas.common import UserSummary

# response of GET /analytics/dashboard. every count is limited to the caller's scope (see routers/analytics.py)

class DashboardScope(str, Enum):
    ALL = "all"            # Facility Admin: every ticket
    ASSIGNED = "assigned"  # Engineer: tickets assigned to them
    REPORTED = "reported"  # Employee: tickets they raised

class AttentionKind(str, Enum):
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    SLA_BREACHED = "sla_breached"
    UNASSIGNED = "unassigned"
    SILENT = "silent"            # no update visible to the reporter for a while
    AWAITING_REPORTER = "awaiting_reporter"  # resolved, the reporter should confirm (close) or reopen

class CountItem(BaseModel):
    key: str
    count: int

# ---------- right now (ignores the date range) ----------

class CurrentSnapshot(BaseModel):
    by_status: dict[IncidentStatus, int]  # Closed is only counted inside the date range, see PeriodStats
    active: int                # Open + In Progress + Blocked
    unassigned: int
    escalated: int
    blocked: int
    critical_or_high: int      # active Critical/High tickets
    sla_breached: int          # active tickets older than their priority's resolve target
    sla_at_risk: int           # active tickets past 75% of their target
    awaiting_reporter: int     # Resolved, waiting on the reporter to close or reopen

class LocationRef(BaseModel):
    facility: str
    building: str
    floor: str | None = None
    seat: str | None = None

class AttentionFlag(BaseModel):
    kind: AttentionKind
    detail: str | None = None

class TicketSummary(BaseModel):
    id: int
    title: str
    status: IncidentStatus
    priority: IncidentPriority
    category: IncidentCategory
    is_escalated: bool
    assignee: UserSummary | None
    reporter: UserSummary
    location: LocationRef
    created_at: datetime
    age_hours: float
    sla_target_hours: float
    flags: list[AttentionFlag]
    last_update_at: datetime   # last status change or public note by someone other than the reporter
    last_update: str | None    # body of the latest public note, if any

# ---------- inside the date range ----------

class Duration(BaseModel):
    median_hours: float | None
    count: int
    previous_median_hours: float | None = None  # same-length window right before, for the trend arrow

class Timings(BaseModel):
    acknowledge: Duration
    assign: Duration
    resolve: Duration

class SlaPriorityRow(BaseModel):
    priority: IncidentPriority
    target_hours: float
    resolved: int
    met: int

class SlaStats(BaseModel):
    resolved: int
    met: int
    met_pct: float | None
    previous_met_pct: float | None = None
    by_priority: list[SlaPriorityRow]

class TrendPoint(BaseModel):
    bucket: datetime  # start of the day/week
    created: int
    resolved: int

class HotspotItem(BaseModel):
    id: int
    label: str
    building_id: int
    facility: str
    count: int
    active: int
    top_category: IncidentCategory
    top_category_count: int
    recurring: bool  # the same kind of issue was reported here more than once in the range

class Hotspots(BaseModel):
    buildings: list[HotspotItem]
    floors: list[HotspotItem]
    seats: list[HotspotItem]

class PeriodStats(BaseModel):
    created: int
    resolved: int
    closed: int
    previous_created: int | None = None
    by_priority: list[CountItem]
    by_category: list[CountItem]
    timings: Timings
    sla: SlaStats
    trend_bucket: str  # "day" or "week"
    trend: list[TrendPoint]
    hotspots: Hotspots

class Communication(BaseModel):
    silent_after_days: int
    active: int
    updated_recently: int
    updated_recently_pct: float | None

class EngineerLoad(BaseModel):
    user_id: int
    display_name: str
    facility_id: int | None
    specialty: IncidentCategory | None
    is_available: bool
    max_open_tickets: int
    active: int
    blocked: int
    critical_or_high: int
    resolved_in_range: int
    load_pct: float  # active / max_open_tickets

class DashboardRange(BaseModel):
    start: datetime | None  # None = all time
    end: datetime
    previous_start: datetime | None

class Dashboard(BaseModel):
    scope: DashboardScope
    range: DashboardRange
    facility_ids: list[int] | None  # admin's facility filter, None = all
    building_id: int | None
    sla_targets_hours: dict[IncidentPriority, float]
    current: CurrentSnapshot
    attention: list[TicketSummary]  # flagged active tickets, most urgent first
    my_tickets: list[TicketSummary] | None  # Employee only: their active + resolved tickets
    period: PeriodStats
    communication: Communication
    workload: list[EngineerLoad] | None  # Admin + Engineer
