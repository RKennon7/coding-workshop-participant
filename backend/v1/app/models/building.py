"""Building model: a building within a facility (campus)."""
from app.models.base import Base
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Building(Base):
    """A building on a campus (table `buildings`).

    Belongs to one Facility and has many Floors. Names are unique per facility, not globally.
    Every Incident references a building, which is also how an incident's facility is determined.
    """
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "Building A", "North Tower"
    is_active: Mapped[bool] = mapped_column(default=True)

    facility: Mapped["Facility"] = relationship(back_populates="buildings")
    floors: Mapped[list["Floor"]] = relationship(back_populates="building")
