"""Request/response schemas for user accounts and authentication (routers/users.py and routers/auth.py)."""
from pydantic import BaseModel, Field

from app.models import UserRole
from app.schemas.common import AcmeEmail, NewPassword, ORMModel

class UserBase(BaseModel):
    """Fields shared by user creation. Email must be an @acme.inc address (see AcmeEmail)."""
    username: str = Field(min_length=3, max_length=50)
    email: AcmeEmail
    role: UserRole = UserRole.EMPLOYEE
    facility_id: int | None = None  # required for Engineers/Employees, optional home facility for admins

# admin creates a user. leave password out to invite them: they set their own via /auth/register
class UserCreate(UserBase):
    """Admin-only: create (invite) a user. Without a password the account stays unregistered until claimed."""
    password: NewPassword | None = None

class UserUpdate(BaseModel):
    """Admin-only PATCH body: only the fields sent are changed (see apply_updates in app/crud.py).

    No password field: users change their own via POST /auth/change-password.
    """
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: AcmeEmail | None = None
    role: UserRole | None = None
    facility_id: int | None = None
    is_active: bool | None = None

class UserRead(ORMModel):
    """A user as returned by the API. Never includes the password hash."""
    id: int
    username: str
    email: str
    role: UserRole
    facility_id: int | None
    is_active: bool
    is_registered: bool  # False = invited but hasn't set a password yet

# GET /auth/me: the logged in user plus their facility's name for the header
class CurrentUserRead(UserRead):
    """Response of GET /auth/me."""
    facility_name: str | None = None

# a new user claims the account an admin created for their email
class RegisterRequest(BaseModel):
    """Body of POST /auth/register: claim an invited account by setting its password."""
    email: AcmeEmail
    password: NewPassword

class PasswordChange(BaseModel):
    """Body of POST /auth/change-password. current_password has no length rules: it is only checked against the hash."""
    current_password: str
    new_password: NewPassword

class Token(BaseModel):
    """OAuth2-style token response from login/register. Send it back as "Authorization: Bearer <access_token>"."""
    access_token: str
    token_type: str = "bearer"
