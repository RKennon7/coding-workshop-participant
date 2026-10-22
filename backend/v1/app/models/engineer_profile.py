from datetime import datetime

from app.models.base import Base
from app.models.incident import IncidentCategory
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

class EngineerProfile(Base):
    __tablename__ = "engineer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    specialty: Mapped[IncidentCategory | None]  # used to suggest an engineer when assigning
    is_available: Mapped[bool] = mapped_column(default=True, index=True)
    max_open_tickets: Mapped[int] = mapped_column(default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # joined so facility_id below is always available (profiles are listed with their facility)
    user: Mapped["User"] = relationship(back_populates="engineer_profile", lazy="joined")

    @property
    def facility_id(self) -> int | None:
        return self.user.facility_id
