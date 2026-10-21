from app.models.base import Base
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Floor(Base):
    __tablename__ = "floors"
    __table_args__ = (UniqueConstraint("building_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # table relationships
    building: Mapped["Building"] = relationship(back_populates="floors")
    seats: Mapped[list["Seat"]] = relationship(back_populates="floor")
