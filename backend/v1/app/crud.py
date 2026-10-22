# small helpers shared by the routers
from fastapi import HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
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

# ---------- server-side paging for list endpoints ----------
# lists stay plain JSON arrays (dropdowns keep working); the total matching row count goes in this header
# so a data grid can show "1–25 of 312" and page through without loading everything
TOTAL_COUNT_HEADER = "X-Total-Count"

def sort_order(sort: str | None, sortable: dict[str, ColumnElement], default: list[ColumnElement]) -> list[ColumnElement]:
    """?sort=field or ?sort=-field (descending), limited to the given columns. the default order breaks ties"""
    if not sort:
        return default
    key = sort.removeprefix("-")
    if key not in sortable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can't sort by '{key}'. Sortable: {', '.join(sorted(sortable))}",
        )
    column = sortable[key]
    return [column.desc() if sort.startswith("-") else column.asc(), *default]

async def paginate(
    db: AsyncSession, response: Response, query: Select, *, order_by: list[ColumnElement], limit: int, offset: int,
) -> Select:
    """counts every row the (filtered, unordered) query matches into the response header, then returns one ordered page"""
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    response.headers[TOTAL_COUNT_HEADER] = str(total)
    return query.order_by(*order_by).limit(limit).offset(offset)
