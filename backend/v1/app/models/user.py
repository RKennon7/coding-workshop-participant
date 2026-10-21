from base import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
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
    is_active: Mapped[bool] = mapped_column(default=True)