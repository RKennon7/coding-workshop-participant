"""FastAPI dependencies used by the routers: database sessions, authentication and role checks.

Routes declare these with Depends(...): get_db for a session, get_current_user for "any logged-in
user", and require_role / require_admin for coarse role gates. Finer rules (which incident fields a
role may edit, which facilities it may see) live in the routers and app/facility_scope.py.
"""
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
    # What is yield and why are we using it? Yield basically can be considered like a try-with-resources
    # statement from Java.
    # When a method requires this, it will call get_db which will return the session, then the operations
    # get executed and then after the other function is finished, it returns here and completes this
    # method, which just means it closes the session.
    # the session never commits on its own: routes call `await db.commit()` themselves, and anything
    # uncommitted is rolled back when the session closes
    async with AsyncSessionLocal() as session:
        yield session

# reads the "Authorization: Bearer <token>" header. tokenUrl only tells the /docs "Authorize" button
# where to log in (POST /auth/token in routers/auth.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the bearer token to an active User.

    Raises 401 (with WWW-Authenticate: Bearer) if the token is missing, invalid, expired, has no
    integer "uid" claim, or belongs to a user who no longer exists or has been deactivated.
    The returned User is attached to the same request-scoped session the route gets from get_db.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        # checks the signature and the "exp" claim
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
    """Build a dependency that returns the current user, or raises 403 if their role isn't in allowed_roles.

    Usage: `user: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER))`.
    The frontend hides the same actions via frontend/src/auth/permissions.js, but this is what enforces them.
    """
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
