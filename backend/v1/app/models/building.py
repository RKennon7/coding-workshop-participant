from base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Building(Base):
    __tablename__ = "buildings"
    __table_args__ = (UniqueConstraint("facility_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    name: Mapped[str]                                 # "Building A", "North Tower"
    is_active: Mapped[bool] = mapped_column(default=True)
    
    facility: Mapped["Facility"] = relationship(back_populates="buildings")
    floors: Mapped[list["Floor"]] = relationship(back_populates="building")