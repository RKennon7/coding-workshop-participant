from app.models.base import Base
from sqlalchemy import String
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
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(default=UserRole.EMPLOYEE, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # only set for users with the ENGINEER role
    engineer_profile: Mapped["EngineerProfile | None"] = relationship(back_populates="user", uselist=False)
