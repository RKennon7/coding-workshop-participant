from base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    buildings: Mapped[list["Building"]] = relationship(back_populates="facility")
