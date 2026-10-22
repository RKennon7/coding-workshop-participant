"""Response schemas for the dashboard endpoints in routers/analytics.py (GET /analytics/dashboard and /analytics/attention).

These are output-only: they're built by hand in the router (not from ORM objects), so they extend
BaseModel rather than ORMModel. Thresholds mentioned below (SLA targets, "silent" days, ...) are
constants at the top of routers/analytics.py.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.models import IncidentCategory, IncidentPriority, IncidentStatus
from app.schemas.common import UserSummary

# response of GET /analytics/dashboard. every count is limited to the caller's scope (see routers/analytics.py)

class DashboardScope(str, Enum):
    """Which tickets the dashboard covers, decided by the caller's role (not chosen by the client)."""
    ALL = "all"            # Facility Admin: every ticket
    ASSIGNED = "assigned"  # Engineer: tickets assigned to them
    REPORTED = "reported"  # Employee: tickets they raised

class AttentionKind(str, Enum):
    """Reasons a live ticket shows up in the "Needs attention" list. A ticket can have several."""
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    SLA_BREACHED = "sla_breached"
    UNASSIGNED = "unassigned"
    SILENT = "silent"            # no update visible to the reporter for a while
    AWAITING_REPORTER = "awaiting_reporter"  # resolved, the reporter should confirm (close) or reopen

class CountItem(BaseModel):
    """A generic (label, count) pair for breakdown charts, e.g. key="High" for by_priority."""
    key: str
    count: int

# ---------- right now (ignores the date range) ----------

class CurrentSnapshot(BaseModel):
    """Live counts of tickets as they are now, regardless of the selected date range."""
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
    """Human-readable location names (not ids) for a ticket summary."""
    facility: str
    building: str
    floor: str | None = None
    seat: str | None = None

class AttentionFlag(BaseModel):
    """One reason a ticket needs attention, with optional text for the UI (e.g. the blocked reason or how long it's been silent)."""
    kind: AttentionKind
    detail: str | None = None

class TicketSummary(BaseModel):
    """A ticket as shown in the attention list and the employee's "my tickets" panel. Ages are wall-clock hours."""
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
    """Median of a lifecycle duration over the tickets in range; median is None when count is 0."""
    median_hours: float | None
    count: int
    previous_median_hours: float | None = None  # same-length window right before, for the trend arrow

class Timings(BaseModel):
    """Time from creation to first acknowledgement, to assignment, and to resolution."""
    acknowledge: Duration
    assign: Duration
    resolve: Duration

class SlaPriorityRow(BaseModel):
    """SLA results for one priority: tickets resolved in range, and how many within target_hours of creation."""
    priority: IncidentPriority
    target_hours: float
    resolved: int
    met: int

class SlaStats(BaseModel):
    """SLA performance over tickets resolved in the range. met_pct is None when nothing was resolved."""
    resolved: int
    met: int
    met_pct: float | None
    previous_met_pct: float | None = None
    by_priority: list[SlaPriorityRow]

class TrendPoint(BaseModel):
    """Tickets created and resolved in one day/week bucket of the trend chart."""
    bucket: datetime  # start of the day/week
    created: int
    resolved: int

class HotspotItem(BaseModel):
    """A building, floor or seat ranked by how many incidents were reported there in the range.

    `id` is that location's id; building_id is always set so the UI can link/filter by building.
    """
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
    """The top locations at each level of the hierarchy (seats only count incidents that named a seat)."""
    buildings: list[HotspotItem]
    floors: list[HotspotItem]
    seats: list[HotspotItem]

class PeriodStats(BaseModel):
    """Everything computed over the selected date range. previous_* fields cover the same-length window just before it."""
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
    """How well reporters are kept informed: active tickets with a staff update in the last silent_after_days."""
    silent_after_days: int
    active: int
    updated_recently: int
    updated_recently_pct: float | None

class EngineerLoad(BaseModel):
    """One engineer's current workload, for the workload table and balancing assignments."""
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
    """The date range the period stats were computed for, echoed back to the client."""
    start: datetime | None  # None = all time
    end: datetime
    previous_start: datetime | None

class Dashboard(BaseModel):
    """Response of GET /analytics/dashboard. Fields that don't apply to the caller's role are None."""
    scope: DashboardScope
    range: DashboardRange
    facility_ids: list[int] | None  # admin's facility filter, None = all
    building_id: int | None
    sla_targets_hours: dict[IncidentPriority, float]
    current: CurrentSnapshot
    attention_counts: "AttentionCounts"  # the list itself: GET /analytics/attention
    my_tickets: list[TicketSummary] | None  # Employee only: their active + resolved tickets
    period: PeriodStats
    communication: Communication
    workload: list[EngineerLoad] | None  # Admin + Engineer

class AttentionCounts(BaseModel):
    """How many tickets are flagged, overall and per kind (a ticket with two flags counts once in total, once per kind)."""
    total: int  # flagged tickets
    by_kind: dict[AttentionKind, int]

# GET /analytics/attention: one page of flagged tickets, most urgent first
class AttentionPage(BaseModel):
    """Response of GET /analytics/attention."""
    total: int  # tickets matching the kind filter (all flagged tickets without one)
    counts: AttentionCounts
    items: list[TicketSummary]

# Dashboard refers to AttentionCounts before it's defined (the string annotation above), so resolve it now
Dashboard.model_rebuild()
