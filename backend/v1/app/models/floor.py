from base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Floor(Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    facility_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # table relationships
    facility: Mapped["Building"] = relationship(back_populates="floors")
    seats: Mapped[list["Seat"]] = relationship(back_populates="floor")