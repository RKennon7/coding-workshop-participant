from pydantic import BaseModel, Field

from app.models import UserRole
from app.schemas.common import AcmeEmail, NewPassword, ORMModel

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: AcmeEmail
    role: UserRole = UserRole.EMPLOYEE
    facility_id: int | None = None  # required for Engineers/Employees, optional home facility for admins

# admin creates a user. leave password out to invite them: they set their own via /auth/register
class UserCreate(UserBase):
    password: NewPassword | None = None

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: AcmeEmail | None = None
    role: UserRole | None = None
    facility_id: int | None = None
    is_active: bool | None = None

class UserRead(ORMModel):
    id: int
    username: str
    email: str
    role: UserRole
    facility_id: int | None
    is_active: bool
    is_registered: bool  # False = invited but hasn't set a password yet

# GET /auth/me: the logged in user plus their facility's name for the header
class CurrentUserRead(UserRead):
    facility_name: str | None = None

# a new user claims the account an admin created for their email
class RegisterRequest(BaseModel):
    email: AcmeEmail
    password: NewPassword

class PasswordChange(BaseModel):
    current_password: str
    new_password: NewPassword

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
