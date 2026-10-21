# small helpers shared by the routers
from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base

# fetch a row by primary key or raise a 404, e.g. await get_or_404(db, Facility, 3)
async def get_or_404[T: Base](db: AsyncSession, model: type[T], obj_id: int) -> T:
    obj = await db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} {obj_id} not found")
    return obj

# copy only the fields the client actually sent onto the ORM object (PATCH semantics)
def apply_updates(obj: Base, payload: BaseModel, exclude: set[str] | None = None) -> None:
    for field, value in payload.model_dump(exclude_unset=True, exclude=exclude).items():
        setattr(obj, field, value)

# field-level RBAC for PATCH endpoints: reject the request if it touches a field the caller may not change
def ensure_fields_allowed(payload: BaseModel, allowed: set[str]) -> None:
    disallowed = payload.model_fields_set - allowed
    if disallowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not permitted to change: {', '.join(sorted(disallowed))}",
        )
