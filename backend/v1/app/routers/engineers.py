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

# ?sort= keys match the engineers grid's column fields
def _user_column(column):
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
    profile = await get_or_404(db, EngineerProfile, profile_id)
    await db.delete(profile)
    await db.commit()
