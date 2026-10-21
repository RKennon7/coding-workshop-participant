from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import apply_updates, get_or_404
from app.dependencies import get_current_user, get_db, require_admin
from app.models import Base, Building, Facility, Floor, Seat, User
from app.schemas.facility import (
    BuildingCreate, BuildingRead, BuildingUpdate,
    FacilityCreate, FacilityRead, FacilityUpdate,
    FloorCreate, FloorRead, FloorUpdate,
    SeatCreate, SeatRead, SeatUpdate,
)

"""
Facility > Building > Floor > Seat all share the same CRUD shape, so one factory builds each router
(the backend twin of createResource in frontend/src/services/resourceService.js):
    GET    /<prefix>         any logged in user (employees need these to report an incident). filters: is_active, <parent>_id
    GET    /<prefix>/{id}    any logged in user
    POST   /<prefix>         Facility Admin
    PATCH  /<prefix>/{id}    Facility Admin
    DELETE /<prefix>/{id}    Facility Admin. 409 if anything still references the row, deactivate it instead
"""

def build_location_router(
    prefix: str,
    model: type[Base],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    parent: tuple[str, type[Base]] | None = None,  # (foreign key field, parent model), e.g. ("facility_id", Facility)
) -> APIRouter:
    router = APIRouter(prefix=f"/{prefix}", tags=["facilities"])
    parent_field, parent_model = parent if parent else (None, None)

    # 404 if the body points at a parent that doesn't exist
    async def check_parent(db: AsyncSession, payload: BaseModel) -> None:
        parent_id = getattr(payload, parent_field, None) if parent_field else None
        if parent_id is not None:
            await get_or_404(db, parent_model, parent_id)

    @router.get("", response_model=list[read_schema])
    async def list_items(
        is_active: bool | None = None,
        parent_id: int | None = Query(default=None, alias=parent_field or "parent_id", include_in_schema=parent is not None),
        limit: int = Query(default=500, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_user),
    ):
        query = select(model).order_by(model.id).limit(limit).offset(offset)
        if is_active is not None:
            query = query.where(model.is_active == is_active)
        if parent_field and parent_id is not None:
            query = query.where(getattr(model, parent_field) == parent_id)
        return list(await db.scalars(query))

    @router.get("/{item_id}", response_model=read_schema)
    async def get_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(get_current_user),
    ):
        return await get_or_404(db, model, item_id)

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    async def create_item(
        payload: create_schema,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ):
        await check_parent(db, payload)
        item = model(**payload.model_dump())
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    @router.patch("/{item_id}", response_model=read_schema)
    async def update_item(
        item_id: int,
        payload: update_schema,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ):
        item = await get_or_404(db, model, item_id)
        await check_parent(db, payload)
        apply_updates(item, payload)
        await db.commit()
        await db.refresh(item)
        return item

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ) -> None:
        item = await get_or_404(db, model, item_id)
        await db.delete(item)
        await db.commit()

    return router


facilities_router = build_location_router("facilities", Facility, FacilityCreate, FacilityUpdate, FacilityRead)
buildings_router = build_location_router(
    "buildings", Building, BuildingCreate, BuildingUpdate, BuildingRead, parent=("facility_id", Facility)
)
floors_router = build_location_router(
    "floors", Floor, FloorCreate, FloorUpdate, FloorRead, parent=("building_id", Building)
)
seats_router = build_location_router(
    "seats", Seat, SeatCreate, SeatUpdate, SeatRead, parent=("floor_id", Floor)
)

routers = [facilities_router, buildings_router, floors_router, seats_router]
