"""
Locations: facilities (campuses), buildings, floors and seats, plus the campus setup wizard.

Facility > Building > Floor > Seat all share the same CRUD shape, so one factory builds each router
(the backend twin of createResource in frontend/src/services/resourceService.js). URL prefixes are
/facilities, /buildings, /floors and /seats:
    GET    /<prefix>         any logged in user (employees need these to report an incident). filters: is_active, <parent>_id,
                             facility_id (admins), q. engineers/employees only ever get their own facility's rows.
                             paged with limit/offset/sort, total in the X-Total-Count header
    GET    /<prefix>/{id}    any logged in user, 404 outside their facility
    POST   /<prefix>         Facility Admin
    PATCH  /<prefix>/{id}    Facility Admin
    DELETE /<prefix>/{id}    Facility Admin. removes everything under it too (facility > buildings > floors > seats).
                             409 if any incident is at that location, deactivate it instead so ticket history is kept.
                             deleting a facility leaves its users without one until an admin reassigns them
    GET    /<prefix>/{id}/delete-impact   Facility Admin. counts of what a delete would remove, for the confirm dialog
Bulk setup (Facility Admin): POST /facilities/setup creates a whole campus in one request, and
POST /facilities/{id}/buildings/bulk adds generated buildings to an existing one.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import apply_updates, get_or_404, paginate, sort_order
from app.dependencies import get_current_user, get_db, require_admin
from app.facility_scope import LOCATION_SCOPES, visible_facility_ids
from app.models import Base, Building, Facility, Floor, Incident, Seat, User
from app.schemas.facility import (
    BuildingCreate, BuildingPlan, BuildingRead, BuildingsBulkCreate, BuildingUpdate,
    DeleteImpact, FacilityCreate, FacilityRead, FacilitySetup, FacilitySetupResult, FacilityUpdate,
    FloorCreate, FloorRead, FloorUpdate,
    SeatCreate, SeatRead, SeatUpdate,
)

def _subtree(model: type[Base], item_id: int) -> tuple[ColumnElement | None, ...]:
    """Conditions selecting everything at or under one location: (buildings, floors, seats, incidents).

    None = that level can't be under it (e.g. a floor has no buildings below it). Each level is an
    IN (subquery) on the level above, so nothing is loaded into Python. Used both to count a delete's
    impact and to perform the delete, so the two always agree.
    """
    if model is Facility:
        buildings = Building.facility_id == item_id
    elif model is Building:
        buildings = Building.id == item_id
    else:
        buildings = None
    if buildings is not None:
        floors = Floor.building_id.in_(select(Building.id).where(buildings))
    else:
        floors = Floor.id == item_id if model is Floor else None
    if floors is not None:
        seats = Seat.floor_id.in_(select(Floor.id).where(floors))
    else:
        seats = Seat.id == item_id
    incidents = {
        Facility: Incident.building_id.in_(select(Building.id).where(Building.facility_id == item_id)),
        Building: Incident.building_id == item_id,
        Floor: Incident.floor_id == item_id,
        Seat: Incident.seat_id == item_id,
    }[model]
    return buildings, floors, seats, incidents

async def _delete_impact(db: AsyncSession, model: type[Base], item_id: int) -> DeleteImpact:
    """Count what deleting this location would remove (and, for a facility, how many users would lose their facility)."""
    buildings, floors, seats, incidents = _subtree(model, item_id)

    async def count(entity, condition) -> int:
        if condition is None:
            return 0
        return await db.scalar(select(func.count()).select_from(entity).where(condition))

    return DeleteImpact(
        buildings=await count(Building, buildings),
        floors=await count(Floor, floors),
        seats=await count(Seat, seats),
        incidents=await count(Incident, incidents),
        users=await count(User, User.facility_id == item_id) if model is Facility else 0,
    )


def build_location_router(
    prefix: str,
    model: type[Base],
    create_schema: type[BaseModel],
    update_schema: type[BaseModel],
    read_schema: type[BaseModel],
    parent: tuple[str, type[Base]] | None = None,  # (foreign key field, parent model), e.g. ("facility_id", Facility)
) -> APIRouter:
    """Build the CRUD router for one location level (see the module docstring for the endpoints).

    The endpoint functions below are defined once and registered on all four routers, so their
    docstrings (shown in /docs) are written generically. Facility scoping comes from
    LOCATION_SCOPES in app/facility_scope.py.
    """
    router = APIRouter(prefix=f"/{prefix}", tags=["facilities"])
    parent_field, parent_model = parent if parent else (None, None)
    in_facilities = LOCATION_SCOPES[model]

    # ?sort= keys match the grid's column fields: the label (name/code), the parent (by its name), active
    label = model.code if model is Seat else model.name
    sortable = {"id": model.id, label.key: label, "is_active": model.is_active}
    searchable = [label]
    if model is Facility:
        sortable["address"] = Facility.address
        searchable.append(Facility.address)
    if parent:
        parent_label = parent_model.name
        sortable[parent_field] = (
            select(parent_label).where(parent_model.id == getattr(model, parent_field)).correlate(model).scalar_subquery()
        )

    # 404 if the body points at a parent that doesn't exist. only checks existence: moving a location
    # to another parent isn't restricted (e.g. incidents at it keep their old building/floor ids)
    async def check_parent(db: AsyncSession, payload: BaseModel) -> None:
        parent_id = getattr(payload, parent_field, None) if parent_field else None
        if parent_id is not None:
            await get_or_404(db, parent_model, parent_id)

    @router.get("", response_model=list[read_schema])
    async def list_items(
        is_active: bool | None = None,
        parent_id: int | None = Query(default=None, alias=parent_field or "parent_id", include_in_schema=parent is not None),
        facility_id: list[int] | None = Query(default=None),
        q: str | None = Query(default=None, description="search name/code"),
        sort: str | None = Query(default=None, description="column to sort by, '-' prefix for descending"),
        limit: int = Query(default=500, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        response: Response = None,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        """List locations of this type. Any logged in user.

        Engineers and employees only get rows at their own facility (their facility_id filter is
        ignored, so it can't widen that); admins see every facility or the ones in facility_id.
        Filters: is_active, the parent id (e.g. facility_id on /buildings, building_id on /floors),
        q (name, code or address). Paged with limit/offset, total in the X-Total-Count header.
        400 for an unknown ?sort= column.
        """
        query = select(model)
        facility_ids = visible_facility_ids(user, facility_id)
        if facility_ids is not None:
            query = query.where(in_facilities(facility_ids))
        if is_active is not None:
            query = query.where(model.is_active == is_active)
        if parent_field and parent_id is not None:
            query = query.where(getattr(model, parent_field) == parent_id)
        if q:
            query = query.where(or_(*(column.ilike(f"%{q}%") for column in searchable)))
        query = await paginate(db, response, query, order_by=sort_order(sort, sortable, [model.id]), limit=limit, offset=offset)
        return list(await db.scalars(query))

    @router.get("/{item_id}", response_model=read_schema)
    async def get_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        """Get one location by id. Any logged in user.

        404 if it doesn't exist or, for engineers/employees, if it's at another facility.
        """
        query = select(model).where(model.id == item_id)
        facility_ids = visible_facility_ids(user)
        if facility_ids is not None:
            query = query.where(in_facilities(facility_ids))
        item = await db.scalar(query)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} {item_id} not found")
        return item

    @router.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    async def create_item(
        payload: create_schema,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ):
        """Create a location. Facility Admin only.

        404 if the parent doesn't exist, 409 if the name/code is already used under the same parent
        (facility names are unique overall).
        """
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
        """Edit a location (PATCH: only the fields sent are changed). Facility Admin only.

        Set is_active=false to retire a location that has incident history instead of deleting it.
        404 if it or a new parent doesn't exist, 409 on a duplicate name/code.
        """
        item = await get_or_404(db, model, item_id)
        await check_parent(db, payload)
        apply_updates(item, payload)
        await db.commit()
        await db.refresh(item)
        return item

    @router.get("/{item_id}/delete-impact", response_model=DeleteImpact)
    async def delete_impact(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ) -> DeleteImpact:
        """What deleting this location would remove, for the confirm dialog. Facility Admin only.

        incidents > 0 means the delete will be refused. users is only counted for facilities.
        404 if the location doesn't exist.
        """
        await get_or_404(db, model, item_id)
        return await _delete_impact(db, model, item_id)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(
        item_id: int,
        db: AsyncSession = Depends(get_db),
        _: User = Depends(require_admin),
    ) -> None:
        """Delete a location and everything under it. Facility Admin only.

        - 404: it doesn't exist
        - 409: any incident is recorded at it or under it. Deactivate it instead, so ticket history is kept
        Deleting a facility leaves its users without a facility until an admin reassigns them.
        """
        item = await get_or_404(db, model, item_id)
        impact = await _delete_impact(db, model, item_id)
        if impact.incidents:
            label = getattr(item, "name", None) or item.code
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{label} has {impact.incidents} incident{'s' if impact.incidents != 1 else ''} recorded against it. "
                       "Deactivate it instead, so its ticket history is kept.",
            )

        # children first so no foreign key is left dangling, all in one transaction.
        # bulk DELETE statements, so ORM cascades/events don't run (the models don't define any here anyway)
        buildings, floors, seats, _incidents = _subtree(model, item_id)
        if model is Facility:
            await db.execute(update(User).where(User.facility_id == item_id).values(facility_id=None))
        for entity, condition in ((Seat, seats), (Floor, floors), (Building, buildings)):
            if condition is not None:
                await db.execute(delete(entity).where(condition))
        await db.execute(delete(model).where(model.id == item_id))
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



# ---------- bulk setup: a whole campus (or more buildings for one) in a single request ----------

# floors are "Floor 1".."Floor N", seats "{code}-{floor}-{seat:02d}" (NT-3-02) -- same scheme as the sample data
def _build(plan: BuildingPlan) -> Building:
    return Building(
        name=plan.name,
        floors=[
            Floor(
                name=f"Floor {floor}",
                seats=[Seat(code=f"{plan.code}-{floor}-{seat:02d}") for seat in range(1, plan.seats_per_floor + 1)],
            )
            for floor in range(1, plan.floors + 1)
        ],
    )

async def _add_buildings(db: AsyncSession, facility: Facility, plans: list[BuildingPlan]) -> FacilitySetupResult:
    """Create the planned buildings (with generated floors and seats) under `facility` and commit.

    `facility` may be new and not yet flushed (id None), in which case it's inserted in the same
    commit. 409 if an existing building at the facility already has one of the names
    (case-insensitive). Duplicates within the plan itself are rejected by the BuildingsBulkCreate schema.
    """
    # friendlier than the unique constraint's generic 409
    if facility.id is not None:
        taken = set(await db.scalars(
            select(func.lower(Building.name)).where(
                Building.facility_id == facility.id, func.lower(Building.name).in_([p.name.lower() for p in plans])
            )
        ))
        if taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{facility.name} already has a building named: {', '.join(sorted(taken))}",
            )
    for plan in plans:
        building = _build(plan)
        building.facility = facility
        db.add(building)
    await db.commit()
    await db.refresh(facility)
    return FacilitySetupResult(
        facility=FacilityRead.model_validate(facility),
        buildings=len(plans),
        floors=sum(p.floors for p in plans),
        seats=sum(p.floors * p.seats_per_floor for p in plans),
    )

@facilities_router.post("/setup", response_model=FacilitySetupResult, status_code=status.HTTP_201_CREATED)
async def setup_facility(
    payload: FacilitySetup,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> FacilitySetupResult:
    """Setup wizard: create a facility with its buildings, floors and seats in one request. Facility Admin only.

    Floors are named "Floor 1".."Floor N" and seats get codes like NT-3-02 from each building's code.
    Everything is created in one transaction, so a failure leaves nothing behind.

    - 409: a facility with that name already exists (case-insensitive)
    - 422: invalid plan, e.g. duplicate building names/codes or more than 5000 seats in total
    """
    if await db.scalar(select(Facility.id).where(func.lower(Facility.name) == payload.name.strip().lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A facility named '{payload.name}' already exists")
    facility = Facility(name=payload.name.strip(), address=payload.address)
    db.add(facility)
    return await _add_buildings(db, facility, payload.buildings)

@facilities_router.post("/{facility_id}/buildings/bulk", response_model=FacilitySetupResult, status_code=status.HTTP_201_CREATED)
async def add_buildings(
    facility_id: int,
    payload: BuildingsBulkCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> FacilitySetupResult:
    """Add generated buildings (with floors and seats) to an existing facility. Facility Admin only.

    Same naming scheme and limits as POST /facilities/setup.
    - 404: the facility doesn't exist
    - 409: the facility already has a building with one of these names (case-insensitive)
    """
    facility = await get_or_404(db, Facility, facility_id)
    return await _add_buildings(db, facility, payload.buildings)


routers = [facilities_router, buildings_router, floors_router, seats_router]
