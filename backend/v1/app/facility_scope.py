"""Multi-campus visibility: which facilities (campuses) a user may see, and how to filter each model down to them.

Admins see every facility and may narrow to some; engineers/employees only ever see their own.
Used by the facilities, engineers, incidents and analytics routers to add WHERE clauses, so rows
outside a user's campus simply don't come back (a lookup by id then 404s rather than 403s, which
doesn't reveal that the row exists).
"""
from sqlalchemy import ColumnElement, Select, false, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Building, Facility, Floor, Incident, Seat, User, UserRole

def visible_facility_ids(user: User, requested: list[int] | None = None) -> list[int] | None:
    """None = no restriction (an admin who didn't pick any). otherwise the facility ids to limit results to

    `requested` is the admin's ?facility_id= filter; it is ignored for non-admins, who always get
    their own facility. An empty list means "nothing is visible".
    """
    if user.role == UserRole.FACILITY_ADMIN:
        return requested or None
    # a non-admin without a facility sees nothing rather than everything
    return [user.facility_id] if user.facility_id is not None else []

# subqueries (not executed here) for use inside IN (...) clauses
def building_ids_in(facility_ids: list[int]) -> Select:
    return select(Building.id).where(Building.facility_id.in_(facility_ids))

def floor_ids_in(facility_ids: list[int]) -> Select:
    return select(Floor.id).where(Floor.building_id.in_(building_ids_in(facility_ids)))

# model -> condition limiting its rows to the given facilities
# (walks up the hierarchy: seat -> floor -> building -> facility). used by the generic routers in routers/facilities.py
LOCATION_SCOPES = {
    Facility: lambda ids: Facility.id.in_(ids),
    Building: lambda ids: Building.facility_id.in_(ids),
    Floor: lambda ids: Floor.building_id.in_(building_ids_in(ids)),
    Seat: lambda ids: Seat.floor_id.in_(floor_ids_in(ids)),
}

def incidents_in(facility_ids: list[int]) -> ColumnElement[bool]:
    # an incident's facility is its building's facility
    return Incident.building_id.in_(building_ids_in(facility_ids)) if facility_ids else false()

def users_in(facility_ids: list[int]) -> ColumnElement[bool]:
    return User.facility_id.in_(facility_ids) if facility_ids else false()

# facility id of a building (None if the building doesn't exist), e.g. to check an assignee works at the incident's campus
async def facility_of_building(db: AsyncSession, building_id: int) -> int | None:
    return await db.scalar(select(Building.facility_id).where(Building.id == building_id))
