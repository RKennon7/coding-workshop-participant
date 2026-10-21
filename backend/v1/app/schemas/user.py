from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    role: UserRole

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"