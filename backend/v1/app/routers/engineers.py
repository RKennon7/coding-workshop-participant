"""
Engineer profiles: the roster used for assigning tickets and balancing workload.

URL prefix: /engineers. A profile adds work details (display name, phone, specialty, availability,
max_open_tickets capacity) to a user account with the Engineer role; at most one per user.

Who may call it: Facility Admins and Engineers can read; only admins create/delete. Engineers may
PATCH their own profile's phone and is_available, nothing else. Employees get 403 on every endpoint.
Visibility: admins see every facility's engineers (optionally filtered by facility_id); engineers only
see colleagues at their own facility. A profile's facility is its user's facility_id.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import apply_updates, ensure_fields_allowed, get_or_404, paginate, sort_order
from app.dependencies import get_db, require_admin, require_role
from app.facility_scope import visible_facility_ids
from app.models import EngineerProfile, Facility, IncidentCategory, User, UserRole
from app.schemas.engineer import EngineerCreate, EngineerRead, EngineerUpdate

router = APIRouter(prefix="/engineers", tags=["engineers"])

# engineers may keep their own contact info + availability up to date, everything else is admin only
ENGINEER_SELF_FIELDS = {"phone", "is_available"}

# ?sort= keys match the engineers grid's column fields. user/facility columns are correlated subqueries
# so sorting by them doesn't need a join on the main query
def _user_column(column):
    """Scalar subquery reading `column` from the profile's user row, usable in ORDER BY."""
    return select(column).where(User.id == EngineerProfile.user_id).correlate(EngineerProfile).scalar_subquery()

ENGINEER_SORTS = {
    "id": EngineerProfile.id,
    "display_name": EngineerProfile.display_name,
    "user_id": _user_column(User.username),
    "facility_id": select(Facility.name).join(User, User.facility_id == Facility.id)
        .where(User.id == EngineerProfile.user_id).correlate(EngineerProfile).scalar_subquery(),
    "specialty": EngineerProfile.specialty,
    "phone": EngineerProfile.phone,
    "is_available": EngineerProfile.is_available,
    "max_open_tickets": EngineerProfile.max_open_tickets,
}

@router.get("", response_model=list[EngineerRead])
async def list_engineers(
    is_available: bool | None = None,
    specialty: IncidentCategory | None = None,
    facility_id: list[int] | None = Query(default=None, description="admins: limit to these facilities"),
    q: str | None = Query(default=None, description="search name or phone"),
    sort: str | None = Query(default=None, description="column to sort by, '-' prefix for descending. default by name"),
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    response: Response = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER)),
) -> list[EngineerProfile]:
    """List engineer profiles. Facility Admin or Engineer.

    Engineers only get colleagues at their own facility; their facility_id filter is ignored, so it
    can't widen what they see. Admins see all facilities, or the ones passed in facility_id.
    Other filters: is_available, specialty, q (name or phone). Paged with limit/offset, total in the
    X-Total-Count header; default order is by display name. 400 for an unknown ?sort= column.
    """
    query = select(EngineerProfile)
    # engineers only see colleagues at their own facility
    facility_ids = visible_facility_ids(current_user, facility_id)
    if facility_ids is not None:
        query = query.join(User, User.id == EngineerProfile.user_id).where(User.facility_id.in_(facility_ids))
    if is_available is not None:
        query = query.where(EngineerProfile.is_available == is_available)
    if specialty is not None:
        query = query.where(EngineerProfile.specialty == specialty)
    if q:
        query = query.where(or_(EngineerProfile.display_name.ilike(f"%{q}%"), EngineerProfile.phone.ilike(f"%{q}%")))
    order_by = sort_order(sort, ENGINEER_SORTS, [EngineerProfile.display_name, EngineerProfile.id])
    query = await paginate(db, response, query, order_by=order_by, limit=limit, offset=offset)
    return list(await db.scalars(query))

@router.get("/{profile_id}", response_model=EngineerRead)
async def get_engineer(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER)),
) -> EngineerProfile:
    """Get one engineer profile. Facility Admin or Engineer.

    404 if it doesn't exist or, for engineers, if it belongs to another facility (404 rather than
    403 so other campuses' profile ids aren't revealed).
    """
    profile = await get_or_404(db, EngineerProfile, profile_id)
    facility_ids = visible_facility_ids(current_user)
    if facility_ids is not None and profile.facility_id not in facility_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"EngineerProfile {profile_id} not found")
    return profile

@router.post("", response_model=EngineerRead, status_code=status.HTTP_201_CREATED)
async def create_engineer(
    payload: EngineerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> EngineerProfile:
    """Create a profile for an Engineer user. Facility Admin only.

    - 400: the user's role isn't Engineer
    - 404: the user doesn't exist
    - 409: the user already has a profile
    """
    user = await get_or_404(db, User, payload.user_id)
    if user.role != UserRole.ENGINEER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' has role '{user.role.value}', only Engineers can have a profile",
        )
    existing = await db.execute(select(EngineerProfile.id).where(EngineerProfile.user_id == user.id))
    if existing.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"User '{user.username}' already has an engineer profile")

    profile = EngineerProfile(**payload.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.patch("/{profile_id}", response_model=EngineerRead)
async def update_engineer(
    profile_id: int,
    payload: EngineerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER)),
) -> EngineerProfile:
    """Edit a profile (PATCH: only the fields sent are changed). Facility Admin or Engineer.

    Admins may change any field. Engineers may only update their own profile, and only phone and
    is_available (403 for someone else's profile or any other field).
    404 if the profile doesn't exist.
    """
    profile = await get_or_404(db, EngineerProfile, profile_id)
    if current_user.role == UserRole.ENGINEER:
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own profile")
        ensure_fields_allowed(payload, ENGINEER_SELF_FIELDS)

    apply_updates(profile, payload)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engineer(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Delete an engineer profile. Facility Admin only. 404 if it doesn't exist.

    Only the profile goes; the user account and their ticket assignments are untouched.
    """
    profile = await get_or_404(db, EngineerProfile, profile_id)
    await db.delete(profile)
    await db.commit()
