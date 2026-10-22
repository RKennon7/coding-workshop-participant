"""Facility model: a campus, the top of the Facility > Building > Floor > Seat hierarchy."""
from app.models.base import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Facility(Base):
    """A campus (table `facilities`), e.g. "ACME HQ Campus". Names are unique.

    Users belong to a facility (User.facility_id) and non-admins only see their own one.
    Set is_active=False to retire a campus instead of deleting it, so ticket history is kept.
    """
    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[str | None]  # no explicit column type: Mapped[str] maps to an unbounded VARCHAR
    is_active: Mapped[bool] = mapped_column(default=True)

    buildings: Mapped[list["Building"]] = relationship(back_populates="facility")
