from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import apply_updates, get_or_404, paginate, sort_order
from app.dependencies import get_db, require_admin
from app.models import Facility, User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.security import hash_password

# user management is admin only. employees/engineers see themselves through /auth/me
router = APIRouter(prefix="/users", tags=["users"])

# friendly 409 for duplicate usernames/emails (the unique constraint would catch it anyway, with a vaguer message)
async def _ensure_unique(db: AsyncSession, username: str | None, email: str | None, exclude_id: int | None = None) -> None:
    for column, value in ((User.username, username), (User.email, email)):
        if value is None:
            continue
        query = select(User.id).where(column == value)
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        if (await db.execute(query)).first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{column.key} '{value}' is already taken",
            )

# engineers/employees only see their own facility, so they must have one. admins may (it's their default view)
async def _check_facility(db: AsyncSession, role: UserRole, facility_id: int | None) -> None:
    if facility_id is None:
        if role != UserRole.FACILITY_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"A facility is required for the {role.value} role")
        return
    await get_or_404(db, Facility, facility_id)

# ?sort= keys match the users grid's column fields
USER_SORTS = {
    "id": User.id,
    "username": User.username,
    "email": User.email,
    "role": User.role,
    "facility_id": select(Facility.name).where(Facility.id == User.facility_id).correlate(User).scalar_subquery(),
    "is_active": User.is_active,
    "is_registered": User.password_hash.is_not(None),
}

@router.get("", response_model=list[UserRead])
async def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    facility_id: list[int] | None = Query(default=None),
    q: str | None = Query(default=None, description="search username or email"),
    sort: str | None = Query(default=None, description="column to sort by, '-' prefix for descending"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[User]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if facility_id:
        query = query.where(User.facility_id.in_(facility_id))
    if q:
        query = query.where(or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    query = await paginate(db, response, query, order_by=sort_order(sort, USER_SORTS, [User.id]), limit=limit, offset=offset)
    return list(await db.scalars(query))

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    return await get_or_404(db, User, user_id)

# without a password the user is invited: they finish signing up themselves at POST /auth/register.
# with a password the account can log in immediately.
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> User:
    await _ensure_unique(db, payload.username, payload.email)
    await _check_facility(db, payload.role, payload.facility_id)
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password) if payload.password else None,
        role=payload.role,
        facility_id=payload.facility_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> User:
    user = await get_or_404(db, User, user_id)
    # stops an admin from accidentally locking themselves out
    if user.id == current_user.id and (
        payload.is_active is False or (payload.role is not None and payload.role != UserRole.FACILITY_ADMIN)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't deactivate or demote yourself")

    await _ensure_unique(db, payload.username, payload.email, exclude_id=user.id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.keys() & {"role", "facility_id"}:
        await _check_facility(db, changes.get("role") or user.role, changes.get("facility_id", user.facility_id))
    apply_updates(user, payload)
    await db.commit()
    await db.refresh(user)
    return user

# users with incidents or notes can't be deleted (409), deactivate them with PATCH is_active=false instead
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    user = await get_or_404(db, User, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't delete yourself")
    await db.delete(user)
    await db.commit()
