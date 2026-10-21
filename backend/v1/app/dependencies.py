from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User, UserRole
from app.security import decode_access_token

# FastAPI dependency: provides an async db session to any route that needs it
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

"""
What is yield and why are we using it? Yield basically can be considered like a try-with-resources statement from Java

When a method requires this, it will call get_db which will return the session, then the operations get executed and then after the other function is 
finished, it returns here and completes this method, which just means it closes the session
"""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_access_token(token)
        # look the user up by id (uid), not by username (sub): usernames can be changed and then reused,
        # which would let an old token log in as whoever has that username now
        user_id = payload.get("uid")
        if not isinstance(user_id, int):
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = await db.get(User, user_id)
    # deactivated users are locked out even if they still hold an unexpired token
    if user is None or not user.is_active:
        raise credentials_exception
    return user

# check if current user has the required role(s)
def require_role(*allowed_roles: UserRole):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role.value}' is not permitted to perform this action"
                ),
            )
        return current_user
    return role_checker

# shorthand for the most common check
require_admin = require_role(UserRole.FACILITY_ADMIN)
