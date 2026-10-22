"""
Authentication: logging in, claiming an invited account, and the caller's own profile.

URL prefix: /auth (served under /api/v1 in AWS). /token and /register are public; /me and
/change-password need a valid bearer token, any role.

Accounts are invite-only: a Facility Admin creates the user (POST /users) and the user then picks
their own password here via /register. Tokens are JWTs signed with HS256 (see app/security.py) and
are checked on every request by get_current_user in app/dependencies.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import Facility, User
from app.schemas.user import CurrentUserRead, PasswordChange, RegisterRequest, Token
from app.security import DUMMY_PASSWORD_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# uid lets the frontend tell which incidents/notes/profiles belong to the logged in user
def _token_for(user: User) -> Token:
    """Issue a bearer token for a user.

    The payload carries sub (username), uid (user id) and role. Only uid is trusted by the backend
    to identify the caller (usernames can change); sub/role are there for the frontend to display
    and to hide UI the role can't use. The role is re-read from the db on every request, so a
    role change takes effect without a new token.
    """
    access_token = create_access_token(data={"sub": user.username, "uid": user.id, "role": user.role.value})
    return Token(access_token=access_token, token_type="bearer")

# login endpoint: use POST. the "username" form field accepts either the username or the email
@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Log in and get a bearer token. Public.

    Takes an OAuth2 password form (`username`, `password`); `username` may be the username or the
    email. Returns 401 with the same message whether the user is unknown, not yet registered,
    deactivated, or the password is wrong, so the response doesn't reveal which accounts exist.
    """
    # find user in the db. emails are stored lowercased (see AcmeEmail), usernames match exactly
    login_name = form_data.username.strip()
    result = await db.execute(
        select(User).where(or_(User.username == login_name, User.email == login_name.lower()))
    )
    user = result.scalar_one_or_none()

    # verify that the user exists, has registered, and the password matches. if not, raise exception.
    # bcrypt always runs (against a dummy hash if there's no real one) so timing doesn't reveal which check failed
    can_log_in = user is not None and user.is_registered and user.is_active
    password_ok = verify_password(form_data.password, user.password_hash if can_log_in else DUMMY_PASSWORD_HASH)
    if not (can_log_in and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return _token_for(user)

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Claim an invited account by choosing a password. Public.

    A Facility Admin must first have created a user for this @acme.inc email without a password.
    Setting the password is what "registers" the account; a token is returned so the user is logged
    in straight away.

    - 400: no active account exists for this email (ask an admin to add you)
    - 409: the account already has a password (log in instead)
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # deactivated accounts get the same answer as unknown ones
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No account has been set up for this email. Ask a Facility Admin to add you.",
        )
    if user.is_registered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account is already registered. Log in instead.",
        )

    user.password_hash = hash_password(payload.password)
    await db.commit()
    return _token_for(user)

@router.get("/me", response_model=CurrentUserRead)
async def read_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUserRead:
    """The logged in user's own account, plus their facility's name for the app header. Any role.

    This is how employees and engineers see their own profile; the /users endpoints are admin only.
    `facility_name` is null for an admin without a home facility.
    """
    facility = await db.get(Facility, current_user.facility_id) if current_user.facility_id else None
    return CurrentUserRead.model_validate(current_user).model_copy(update={"facility_name": facility.name if facility else None})

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Change the caller's own password. Any role.

    Requires the current password (400 if it's wrong). Tokens already issued stay valid until
    they expire; there is no token revocation.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
