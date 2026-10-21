from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.user import PasswordChange, RegisterRequest, Token, UserRead
from app.security import DUMMY_PASSWORD_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# uid lets the frontend tell which incidents/notes/profiles belong to the logged in user
def _token_for(user: User) -> Token:
    access_token = create_access_token(data={"sub": user.username, "uid": user.id, "role": user.role.value})
    return Token(access_token=access_token, token_type="bearer")

# login endpoint: use POST. the "username" form field accepts either the username or the email
@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    # find user in the db:
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

# public endpoint: a new user claims the account a Facility Admin created for their email
# by choosing their own password. returns a token so they're logged in straight away.
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

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

@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user

@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
