from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import apply_updates, ensure_fields_allowed, get_or_404
from app.dependencies import get_db, require_admin, require_role
from app.models import EngineerProfile, IncidentCategory, User, UserRole
from app.schemas.engineer import EngineerCreate, EngineerRead, EngineerUpdate

router = APIRouter(prefix="/engineers", tags=["engineers"])

# engineers may keep their own contact info + availability up to date, everything else is admin only
ENGINEER_SELF_FIELDS = {"phone", "is_available"}

@router.get("", response_model=list[EngineerRead])
async def list_engineers(
    is_available: bool | None = None,
    specialty: IncidentCategory | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER)),
) -> list[EngineerProfile]:
    query = select(EngineerProfile).order_by(EngineerProfile.display_name)
    if is_available is not None:
        query = query.where(EngineerProfile.is_available == is_available)
    if specialty is not None:
        query = query.where(EngineerProfile.specialty == specialty)
    return list(await db.scalars(query))

@router.get("/{profile_id}", response_model=EngineerRead)
async def get_engineer(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.FACILITY_ADMIN, UserRole.ENGINEER)),
) -> EngineerProfile:
    return await get_or_404(db, EngineerProfile, profile_id)

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
