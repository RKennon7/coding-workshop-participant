from app.models.base import Base
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

class UserRole(str, Enum):
    FACILITY_ADMIN = "Facility Admin"
    ENGINEER = "Engineer"
    EMPLOYEE = "Employee"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # None until the user registers: admins invite by email, the user sets their own password via /auth/register
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(default=UserRole.EMPLOYEE, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    # the campus the user works at: required for Engineers/Employees, who only see that facility's locations.
    # optional for Facility Admins, where it's just the facility their filters start on (they can see every facility)
    facility_id: Mapped[int | None] = mapped_column(ForeignKey("facilities.id"), index=True)

    # only set for users with the ENGINEER role
    engineer_profile: Mapped["EngineerProfile | None"] = relationship(back_populates="user", uselist=False)

    @property
    def is_registered(self) -> bool:
        return self.password_hash is not None
