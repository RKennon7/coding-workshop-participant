from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.crud import apply_updates, ensure_fields_allowed, get_or_404
from app.dependencies import get_current_user, get_db, require_admin
from app.models import (
    Building,
    Floor,
    Incident,
    IncidentCategory,
    IncidentNote,
    IncidentPriority,
    IncidentStatus,
    IncidentStatusHistory,
    Seat,
    User,
    UserRole,
)
from app.schemas.incident import (
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
    NoteCreate,
    NoteRead,
    NoteUpdate,
    StatusHistoryRead,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])

S = IncidentStatus

# the ticket workflow: which statuses each status can move to (for every role)
ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    S.OPEN: {S.IN_PROGRESS, S.BLOCKED, S.RESOLVED, S.CLOSED},
    S.IN_PROGRESS: {S.OPEN, S.BLOCKED, S.RESOLVED},
    S.BLOCKED: {S.IN_PROGRESS, S.RESOLVED},
    S.RESOLVED: {S.OPEN, S.IN_PROGRESS, S.CLOSED},  # -> Open/In Progress = reopened
    S.CLOSED: {S.OPEN},
}

# how the caller relates to a ticket decides what they may change on it
class Actor(str, Enum):
    ADMIN = "admin"
    ASSIGNEE = "assignee"  # the engineer working the ticket
    REPORTER = "reporter"  # the employee who raised it

EDITABLE_FIELDS: dict[Actor, set[str]] = {
    Actor.ADMIN: set(IncidentUpdate.model_fields),
    Actor.ASSIGNEE: {"status", "blocked_reason"},
    Actor.REPORTER: {
        "title", "description", "category", "priority", "is_escalated", "escalation_reason",
        "status", "building_id", "floor_id", "seat_id",
    },
}

# reporter/assignee/history authors are embedded in responses, so load them with the incident
INCIDENT_LOAD = (joinedload(Incident.reporter), joinedload(Incident.assignee))


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

# row-level RBAC: admins see everything, engineers see tickets assigned to (or raised by) them,
# employees see only their own
def _visible_to(user: User) -> ColumnElement[bool]:
    if user.role == UserRole.FACILITY_ADMIN:
        return true()
    if user.role == UserRole.ENGINEER:
        return or_(Incident.assignee_id == user.id, Incident.reporter_id == user.id)
    return Incident.reporter_id == user.id

# 404 (not 403) for incidents the user can't see, so ids of other people's tickets aren't revealed
async def _get_visible_incident(db: AsyncSession, incident_id: int, user: User) -> Incident:
    query = (
        select(Incident)
        .options(*INCIDENT_LOAD)
        .where(Incident.id == incident_id, _visible_to(user))
        # re-read from the db even if the object is cached, so server-set columns (updated_at) are fresh
        .execution_options(populate_existing=True)
    )
    incident = (await db.execute(query)).scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")
    return incident

def _actor_for(user: User, incident: Incident) -> Actor:
    if user.role == UserRole.FACILITY_ADMIN:
        return Actor.ADMIN
    if user.role == UserRole.ENGINEER and incident.assignee_id == user.id:
        return Actor.ASSIGNEE
    if incident.reporter_id == user.id:
        return Actor.REPORTER
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can't modify this incident")

def _can_see_internal_notes(user: User) -> bool:
    return user.role in (UserRole.FACILITY_ADMIN, UserRole.ENGINEER)

# building is required, floor/seat optional, but each must sit inside the one above it
async def _validate_location(db: AsyncSession, incident: Incident) -> None:
    await get_or_404(db, Building, incident.building_id)
    if incident.floor_id is not None:
        floor = await get_or_404(db, Floor, incident.floor_id)
        if floor.building_id != incident.building_id:
            raise _bad_request(f"Floor {floor.id} is not in building {incident.building_id}")
    if incident.seat_id is not None:
        if incident.floor_id is None:
            raise _bad_request("A seat can only be set together with its floor")
        seat = await get_or_404(db, Seat, incident.seat_id)
        if seat.floor_id != incident.floor_id:
            raise _bad_request(f"Seat {seat.id} is not on floor {incident.floor_id}")

async def _validate_assignee(db: AsyncSession, assignee_id: int) -> None:
    assignee = await get_or_404(db, User, assignee_id)
    if assignee.role != UserRole.ENGINEER or not assignee.is_active:
        raise _bad_request(f"User '{assignee.username}' is not an active Engineer")

# moves the incident to a new status: enforces the workflow, stamps lifecycle timestamps, and writes history
def _change_status(db: AsyncSession, incident: Incident, new_status: IncidentStatus, actor: Actor, user: User) -> None:
    old_status = incident.status
    if new_status == old_status:
        return
    if new_status not in ALLOWED_TRANSITIONS[old_status]:
        raise _bad_request(f"An incident can't move from '{old_status.value}' to '{new_status.value}'")
    if actor == Actor.REPORTER and not (old_status == S.RESOLVED and new_status in (S.OPEN, S.CLOSED)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reporters can only close or reopen an incident once it's resolved",
        )
    if actor == Actor.ASSIGNEE and S.CLOSED in (old_status, new_status):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Engineers can't close or reopen closed incidents, the reporter or an admin closes them",
        )

    now = datetime.now(timezone.utc)
    if incident.acknowledged_at is None:
        incident.acknowledged_at = now  # first time anyone actions the ticket
    if new_status == S.RESOLVED:
        incident.resolved_at = now
    elif new_status == S.CLOSED:
        incident.closed_at = now
    else:
        # back in the queue (reopened or still being worked): it is no longer resolved/closed
        incident.resolved_at = None
        incident.closed_at = None

    incident.status = new_status
    db.add(IncidentStatusHistory(
        incident_id=incident.id,
        from_status=old_status,
        to_status=new_status,
        changed_by_id=user.id,
        reason=incident.blocked_reason if new_status == S.BLOCKED else None,
    ))

# a blocked/escalated ticket must say why, and the reason is cleared once it no longer applies
def _check_reasons(incident: Incident) -> None:
    if incident.status == S.BLOCKED and not incident.blocked_reason:
        raise _bad_request("blocked_reason is required when an incident is Blocked")
    if incident.status != S.BLOCKED:
        incident.blocked_reason = None
    if incident.is_escalated and not incident.escalation_reason:
        raise _bad_request("escalation_reason is required when escalating an incident")
    if not incident.is_escalated:
        incident.escalation_reason = None


# ---------- incidents ----------

@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    status_filter: list[IncidentStatus] | None = Query(default=None, alias="status"),
    priority: list[IncidentPriority] | None = Query(default=None),
    category: list[IncidentCategory] | None = Query(default=None),
    building_id: int | None = None,
    floor_id: int | None = None,
    seat_id: int | None = None,
    assignee_id: int | None = None,
    reporter_id: int | None = None,
    unassigned: bool | None = None,
    is_escalated: bool | None = None,
    q: str | None = Query(default=None, description="search title and description"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Incident]:
    query = (
        select(Incident)
        .options(*INCIDENT_LOAD)
        .where(_visible_to(current_user))
        .order_by(Incident.created_at.desc(), Incident.id.desc())
        .limit(limit)
        .offset(offset)
    )
    # multi-value filters, e.g. ?status=Open&status=Blocked
    if status_filter:
        query = query.where(Incident.status.in_(status_filter))
    if priority:
        query = query.where(Incident.priority.in_(priority))
    if category:
        query = query.where(Incident.category.in_(category))
    for column, value in (
        (Incident.building_id, building_id),
        (Incident.floor_id, floor_id),
        (Incident.seat_id, seat_id),
        (Incident.assignee_id, assignee_id),
        (Incident.reporter_id, reporter_id),
        (Incident.is_escalated, is_escalated),
    ):
        if value is not None:
            query = query.where(column == value)
    if unassigned is not None:
        query = query.where(Incident.assignee_id.is_(None) if unassigned else Incident.assignee_id.is_not(None))
    if q:
        query = query.where(or_(Incident.title.ilike(f"%{q}%"), Incident.description.ilike(f"%{q}%")))
    return list(await db.scalars(query))

@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    return await _get_visible_incident(db, incident_id, current_user)

# anyone can report an incident. it always starts Open and unassigned, with the caller as reporter
@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    incident = Incident(**payload.model_dump(), reporter_id=current_user.id, status=S.OPEN)
    await _validate_location(db, incident)
    db.add(incident)
    await db.flush()  # assigns incident.id for the history row
    db.add(IncidentStatusHistory(incident_id=incident.id, from_status=None, to_status=S.OPEN, changed_by_id=current_user.id))
    await db.commit()
    return await _get_visible_incident(db, incident.id, current_user)

@router.patch("/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Incident:
    incident = await _get_visible_incident(db, incident_id, current_user)
    actor = _actor_for(current_user, incident)
    ensure_fields_allowed(payload, EDITABLE_FIELDS[actor])
    if actor == Actor.REPORTER and incident.status == S.CLOSED:
        raise _bad_request("Closed incidents can't be edited. Ask a Facility Admin to reopen it")

    changes = payload.model_fields_set
    old_assignee_id = incident.assignee_id
    if "assignee_id" in changes and payload.assignee_id is not None:
        await _validate_assignee(db, payload.assignee_id)

    # status goes through the workflow below, every other field is copied as-is
    apply_updates(incident, payload, exclude={"status"})

    if changes & {"building_id", "floor_id", "seat_id"}:
        await _validate_location(db, incident)
    if incident.assignee_id != old_assignee_id:
        incident.assigned_at = datetime.now(timezone.utc) if incident.assignee_id is not None else None
    if payload.status is not None:
        _change_status(db, incident, payload.status, actor, current_user)
    _check_reasons(incident)

    await db.commit()
    return await _get_visible_incident(db, incident.id, current_user)

@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    incident = await get_or_404(db, Incident, incident_id)
    await db.delete(incident)  # notes and status history cascade
    await db.commit()

# the ticket's full workflow trail, oldest first -- for the timeline view
@router.get("/{incident_id}/history", response_model=list[StatusHistoryRead])
async def get_incident_history(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IncidentStatusHistory]:
    await _get_visible_incident(db, incident_id, current_user)
    query = (
        select(IncidentStatusHistory)
        .options(joinedload(IncidentStatusHistory.changed_by))
        .where(IncidentStatusHistory.incident_id == incident_id)
        .order_by(IncidentStatusHistory.changed_at, IncidentStatusHistory.id)
    )
    return list(await db.scalars(query))


# ---------- notes: /incidents/{incident_id}/notes ----------
# anyone who can see the incident can read and add notes. internal notes are engineer/admin only.

async def _get_note(db: AsyncSession, incident_id: int, note_id: int, user: User) -> IncidentNote:
    query = (
        select(IncidentNote)
        .options(joinedload(IncidentNote.author))
        .where(IncidentNote.id == note_id, IncidentNote.incident_id == incident_id)
        .execution_options(populate_existing=True)
    )
    if not _can_see_internal_notes(user):
        query = query.where(IncidentNote.is_internal.is_(False))
    note = (await db.execute(query)).scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found")
    return note

def _check_internal_flag(user: User, is_internal: bool | None) -> None:
    if is_internal and not _can_see_internal_notes(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only engineers and admins can write internal notes")

@router.get("/{incident_id}/notes", response_model=list[NoteRead])
async def list_notes(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[IncidentNote]:
    await _get_visible_incident(db, incident_id, current_user)
    query = (
        select(IncidentNote)
        .options(joinedload(IncidentNote.author))
        .where(IncidentNote.incident_id == incident_id)
        .order_by(IncidentNote.created_at, IncidentNote.id)
    )
    if not _can_see_internal_notes(current_user):
        query = query.where(IncidentNote.is_internal.is_(False))
    return list(await db.scalars(query))

@router.post("/{incident_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    incident_id: int,
    payload: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentNote:
    incident = await _get_visible_incident(db, incident_id, current_user)
    _check_internal_flag(current_user, payload.is_internal)
    if incident.status == S.CLOSED and current_user.role != UserRole.FACILITY_ADMIN:
        raise _bad_request("Notes can't be added to a closed incident")

    note = IncidentNote(incident_id=incident.id, author_id=current_user.id, **payload.model_dump())
    db.add(note)
    await db.commit()
    return await _get_note(db, incident_id, note.id, current_user)

# authors can edit their own notes
@router.patch("/{incident_id}/notes/{note_id}", response_model=NoteRead)
async def update_note(
    incident_id: int,
    note_id: int,
    payload: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IncidentNote:
    await _get_visible_incident(db, incident_id, current_user)
    note = await _get_note(db, incident_id, note_id, current_user)
    if note.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own notes")
    _check_internal_flag(current_user, payload.is_internal)

    apply_updates(note, payload)
    await db.commit()
    return await _get_note(db, incident_id, note.id, current_user)

# authors can delete their own notes, admins can delete any
@router.delete("/{incident_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    incident_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await _get_visible_incident(db, incident_id, current_user)
    note = await _get_note(db, incident_id, note_id, current_user)
    if note.author_id != current_user.id and current_user.role != UserRole.FACILITY_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own notes")
    await db.delete(note)
    await db.commit()
