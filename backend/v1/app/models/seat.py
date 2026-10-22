"""Seat model: a desk/workstation on a floor, the most specific location an incident can have."""
from app.models.base import Base
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Seat(Base):
    """A seat/desk on a floor (table `seats`), identified by a code unique per floor.

    The setup wizard generates codes as "{building code}-{floor}-{seat:02d}", e.g. NT-3-02
    (see app/schemas/facility.py); manually created seats can use any code.
    """
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("floor_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    floor_id: Mapped[int] = mapped_column(ForeignKey("floors.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # "3-A-12"
    is_active: Mapped[bool] = mapped_column(default=True)

    floor: Mapped["Floor"] = relationship(back_populates="seats")
