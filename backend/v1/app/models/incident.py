from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class IncidentStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    BLOCKED = "Blocked"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class IncidentPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class IncidentCategory(str, Enum):
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

    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)  # engineer

    # building is required; floor/seat are optional since not every issue is at a desk.
    # all three are stored directly so "most issues per building/floor/seat" is a simple GROUP BY.
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False, index=True)
    floor_id: Mapped[int | None] = mapped_column(ForeignKey("floors.id"), index=True)
    seat_id: Mapped[int | None] = mapped_column(ForeignKey("seats.id"), index=True)

    # lifecycle timestamps -- used for time-to-acknowledge/assign/resolve reporting.
    # IncidentStatusHistory holds the full audit trail; these are kept so dashboards don't have to scan it.
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
