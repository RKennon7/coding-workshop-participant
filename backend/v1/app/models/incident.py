"""Incident model (a ticket) and its status / priority / category enums.

The workflow rules (allowed transitions, who may edit what) are not in the model: they live in
app/routers/incidents.py and are mirrored for the UI in frontend/src/auth/incidentRules.js.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# the values are what the API sends and the frontend displays. the database stores the member *names*
# (e.g. 'IN_PROGRESS') as native Postgres enum types -- adding a member to an existing database needs
# an ALTER TYPE, which create_all won't do (see scripts/create_tables.py)

class IncidentStatus(str, Enum):
    """Ticket lifecycle. Typical path: Open -> In Progress (<-> Blocked) -> Resolved -> Closed.

    Resolved and Closed tickets can be reopened; the full set of allowed moves is ALLOWED_TRANSITIONS
    in app/routers/incidents.py.

    Open, In Progress and Blocked count as "active" on the dashboard.
    """
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class IncidentPriority(str, Enum):
    """Urgency. Each priority has its own SLA resolve target (defined in app/routers/analytics.py)."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class IncidentCategory(str, Enum):
    """Kind of issue. Also used as an engineer's specialty (EngineerProfile.specialty)."""
    HVAC = "HVAC"
    ELECTRICAL = "Electrical"
    PLUMBING = "Plumbing"
    FURNITURE = "Furniture"
    CLEANING = "Cleaning"
    SECURITY_ACCESS = "Security / Access"
    NETWORK = "Network / Wi-Fi"
    HARDWARE = "Hardware"
    AV_EQUIPMENT = "AV Equipment"
    OTHER = "Other"

class Incident(Base):
    """A reported facility/workplace issue (table `incidents`).

    Belongs to a reporter (any user) and optionally an assignee (an engineer's user id). Location is
    building (required) plus optional floor and seat; the routers check they nest correctly.
    Notes and status history are owned by the incident and deleted with it.
    """
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[IncidentCategory] = mapped_column(index=True)
    priority: Mapped[IncidentPriority] = mapped_column(default=IncidentPriority.MEDIUM, index=True)
    status: Mapped[IncidentStatus] = mapped_column(default=IncidentStatus.OPEN, index=True)

    # why the ticket is stuck / was escalated -- answers "which are escalated or blocked and why?"
    # blocked_reason is the *current* reason (clear it when unblocked); past reasons live in status_history
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    is_escalated: Mapped[bool] = mapped_column(default=False, index=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text)

    # two foreign keys to users, so each relationship below has to say which one it uses (foreign_keys=...)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # engineer

    # building is required; floor/seat are optional since not every issue is at a desk.
    # all three are stored directly so "most issues per building/floor/seat" is a simple GROUP BY.
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False, index=True)
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id"), index=True)
    seat_id: Mapped[int | None] = mapped_column(ForeignKey("seats.id"), index=True)

    # lifecycle timestamps -- used for time-to-acknowledge/assign/resolve reporting.
    # IncidentStatusHistory holds the full audit trail; these are kept so dashboards don't have to scan it.
    # acknowledged_at: first status change by anyone. assigned_at: when the *current* assignee was set.
    # resolved_at / closed_at: cleared again if the ticket is reopened (see _change_status in routers/incidents.py)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # table relationships
    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    building: Mapped["Building"] = relationship()
    floor: Mapped["Floor | None"] = relationship()
    seat: Mapped["Seat | None"] = relationship()
    notes: Mapped[list["IncidentNote"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="IncidentNote.created_at"
    )
    status_history: Mapped[list["IncidentStatusHistory"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan", order_by="IncidentStatusHistory.changed_at"
    )
