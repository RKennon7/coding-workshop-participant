"""User model and the three roles (personas) that drive all access control."""
from app.models.base import Base
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum

class UserRole(str, Enum):
    """The three personas. The value is what the API and JWT "role" claim carry.

    Mirrored by ROLES in frontend/src/auth/permissions.js -- keep the two in sync. In the database the
    enum member *name* is stored (e.g. 'FACILITY_ADMIN'), which is what raw SQL must use (see scripts/create_tables.py).
    """
    FACILITY_ADMIN = "Facility Admin"
    ENGINEER = "Engineer"
    EMPLOYEE = "Employee"

class User(Base):
    """An account (table `users`). Username and email are each unique.

    Accounts are invite-only: a Facility Admin creates the row, optionally without a password, and the
    person claims it via POST /auth/register. Engineers additionally have an EngineerProfile.
    Deactivating (is_active=False) is the usual way to remove access: inactive users can't log in and
    their existing tokens stop working (see app/dependencies.py). A hard delete is refused by the
    foreign keys once the user has reported, been assigned or written anything.
    """
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
        """True once the user has a password, i.e. has finished registering (or an admin set one)."""
        return self.password_hash is not None
