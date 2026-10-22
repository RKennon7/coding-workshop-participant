"""IncidentStatusHistory model: the audit trail of every status change on a ticket."""
from datetime import datetime

from app.models.base import Base
from app.models.incident import IncidentStatus
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

class IncidentStatusHistory(Base):
    """One row per status transition (table `incident_status_history`), append-only.

    Written by the incidents router whenever status changes, plus a first row when the ticket is
    created. Deleted along with its incident (ON DELETE CASCADE). Incident.status_history returns
    rows ordered by changed_at.
    """
    __tablename__ = "incident_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[IncidentStatus | None]  # None for the initial "created as Open" row
    to_status: Mapped[IncidentStatus]
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)  # e.g. why it was blocked or reopened
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # table relationships
    incident: Mapped["Incident"] = relationship(back_populates="status_history")
    changed_by: Mapped["User"] = relationship()
