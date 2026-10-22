from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import ColumnElement, and_, case, func, literal, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.dependencies import get_current_user, get_db
from app.facility_scope import incidents_in, users_in, visible_facility_ids
from app.models import (
    Building,
    EngineerProfile,
    Facility,
    Floor,
    Incident,
    IncidentNote,
    IncidentPriority,
    IncidentStatus,
    IncidentStatusHistory,
    Seat,
    User,
    UserRole,
)
from app.schemas.analytics import (
    AttentionFlag,
    AttentionKind,
    CountItem,
    Communication,
    CurrentSnapshot,
    Dashboard,
    DashboardRange,
    DashboardScope,
    Duration,
    EngineerLoad,
    HotspotItem,
    Hotspots,
    LocationRef,
    PeriodStats,
    SlaPriorityRow,
    SlaStats,
    TicketSummary,
    Timings,
    TrendPoint,
)
from app.schemas.common import UserSummary

"""
One endpoint that answers the dashboard's questions in a single round trip:
    GET /analytics/dashboard?start=&end=&facility_id=&building_id=&tz=
Everything is limited to the caller's scope: admins see every ticket (or the facilities they pick), engineers the tickets assigned
to them, employees the tickets they reported. "current" is the live state and ignores the date range;
"period" only counts tickets created/resolved inside it.
"""

router = APIRouter(prefix="/analytics", tags=["analytics"])

S = IncidentStatus
P = IncidentPriority

# resolve-time targets per priority (wall-clock hours). the frontend reads them from the response
SLA_TARGET_HOURS: dict[IncidentPriority, float] = {P.CRITICAL: 4, P.HIGH: 24, P.MEDIUM: 72, P.LOW: 120}
SLA_AT_RISK_FRACTION = 0.75
SILENT_AFTER_DAYS = 3        # active ticket with no update the reporter can see
UNASSIGNED_AFTER_HOURS = 24  # Critical/High are flagged as soon as they're unassigned
RECURRING_MIN = 2            # same category this many times at one location in the range = recurring
HOTSPOT_LIMIT = 8
ATTENTION_LIMIT = 25
DAILY_TREND_MAX_DAYS = 62    # longer ranges are bucketed by week

ACTIVE = (S.OPEN, S.IN_PROGRESS, S.BLOCKED)
URGENT = (P.CRITICAL, P.HIGH)
PRIORITY_RANK = {P.CRITICAL: 0, P.HIGH: 1, P.MEDIUM: 2, P.LOW: 3}
FLAG_RANK = {
    AttentionKind.SLA_BREACHED: 0,
    AttentionKind.BLOCKED: 1,
    AttentionKind.ESCALATED: 2,
    AttentionKind.UNASSIGNED: 3,
    AttentionKind.AWAITING_REPORTER: 4,
    AttentionKind.SILENT: 5,
}


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

def _scope_for(user: User) -> tuple[DashboardScope, ColumnElement[bool]]:
    if user.role == UserRole.FACILITY_ADMIN:
        return DashboardScope.ALL, true()
    if user.role == UserRole.ENGINEER:
        return DashboardScope.ASSIGNED, Incident.assignee_id == user.id
    return DashboardScope.REPORTED, Incident.reporter_id == user.id

def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def _in_range(column, start: datetime | None, end: datetime) -> ColumnElement[bool]:
    return and_(column >= start, column < end) if start is not None else column < end

def _hours(seconds: float | None) -> float | None:
    return round(seconds / 3600, 2) if seconds is not None else None

# "45m", "5h", "3d" for flag details
def _humanize_hours(hours: float) -> str:
    if hours < 1:
        return f"{max(1, round(hours * 60))}m"
    if hours < 48:
        return f"{hours:.0f}h"
    return f"{hours / 24:.0f}d"

def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


# ---------- "what the reporter has heard" subqueries ----------
# staff updates = status changes and public notes by anyone other than the ticket's reporter

def _staff_note_at(aggregate):
    return (
        select(aggregate(IncidentNote.created_at))
        .where(
            IncidentNote.incident_id == Incident.id,
            IncidentNote.is_internal.is_(False),
            IncidentNote.author_id != Incident.reporter_id,
        )
        .correlate(Incident)
        .scalar_subquery()
    )

def _last_staff_status_at():
    return (
        select(func.max(IncidentStatusHistory.changed_at))
        .where(
            IncidentStatusHistory.incident_id == Incident.id,
            IncidentStatusHistory.from_status.is_not(None),
            IncidentStatusHistory.changed_by_id != Incident.reporter_id,
        )
        .correlate(Incident)
        .scalar_subquery()
    )

def _last_staff_note_body():
    return (
        select(IncidentNote.body)
        .where(
            IncidentNote.incident_id == Incident.id,
            IncidentNote.is_internal.is_(False),
            IncidentNote.author_id != Incident.reporter_id,
        )
        .order_by(IncidentNote.created_at.desc(), IncidentNote.id.desc())
        .limit(1)
        .correlate(Incident)
        .scalar_subquery()
    )


# ---------- live tickets: snapshot, attention list, my tickets ----------

def _flags(incident: Incident, scope: DashboardScope, age_hours: float, idle_hours: float) -> list[AttentionFlag]:
    flags: list[AttentionFlag] = []
    if incident.status == S.RESOLVED:
        if scope == DashboardScope.REPORTED:
            flags.append(AttentionFlag(kind=AttentionKind.AWAITING_REPORTER, detail="Confirm the fix to close it, or reopen it"))
        return flags

    target = SLA_TARGET_HOURS[incident.priority]
    if age_hours > target:
        flags.append(AttentionFlag(kind=AttentionKind.SLA_BREACHED, detail=f"Open {_humanize_hours(age_hours)}, target is {_humanize_hours(target)}"))
    if incident.status == S.BLOCKED:
        flags.append(AttentionFlag(kind=AttentionKind.BLOCKED, detail=incident.blocked_reason))
    if incident.is_escalated:
        flags.append(AttentionFlag(kind=AttentionKind.ESCALATED, detail=incident.escalation_reason))
    if incident.assignee_id is None and (incident.priority in URGENT or age_hours > UNASSIGNED_AFTER_HOURS):
        flags.append(AttentionFlag(kind=AttentionKind.UNASSIGNED, detail=f"Waiting {_humanize_hours(age_hours)} for an engineer"))
    if idle_hours > SILENT_AFTER_DAYS * 24:
        flags.append(AttentionFlag(kind=AttentionKind.SILENT, detail=f"No update for {_humanize_hours(idle_hours)}"))
    return flags

async def _live_tickets(db: AsyncSession, where: list, scope: DashboardScope, now: datetime) -> list[TicketSummary]:
    last_note_at = _staff_note_at(func.max)
    last_status_at = _last_staff_status_at()
    query = (
        select(Incident, last_note_at, last_status_at, _last_staff_note_body())
        .options(
            joinedload(Incident.reporter),
            joinedload(Incident.assignee),
            joinedload(Incident.building).joinedload(Building.facility),
            joinedload(Incident.floor),
            joinedload(Incident.seat),
        )
        .where(*where, Incident.status.in_((*ACTIVE, S.RESOLVED)))
    )
    tickets = []
    for incident, note_at, status_at, note_body in (await db.execute(query)).all():
        last_update_at = max(t for t in (incident.created_at, note_at, status_at) if t is not None)
        age_hours = (now - incident.created_at).total_seconds() / 3600
        idle_hours = (now - last_update_at).total_seconds() / 3600
        tickets.append(TicketSummary(
            id=incident.id,
            title=incident.title,
            status=incident.status,
            priority=incident.priority,
            category=incident.category,
            is_escalated=incident.is_escalated,
            assignee=UserSummary.model_validate(incident.assignee) if incident.assignee else None,
            reporter=UserSummary.model_validate(incident.reporter),
            location=LocationRef(
                facility=incident.building.facility.name,
                building=incident.building.name,
                floor=incident.floor.name if incident.floor else None,
                seat=incident.seat.code if incident.seat else None,
            ),
            created_at=incident.created_at,
            age_hours=round(age_hours, 1),
            sla_target_hours=SLA_TARGET_HOURS[incident.priority],
            flags=_flags(incident, scope, age_hours, idle_hours),
            last_update_at=last_update_at,
            last_update=note_body,
        ))
    return tickets

def _snapshot(tickets: list[TicketSummary]) -> CurrentSnapshot:
    active = [t for t in tickets if t.status in ACTIVE]
    by_status = {s: 0 for s in (*ACTIVE, S.RESOLVED)}
    for t in tickets:
        by_status[t.status] += 1
    return CurrentSnapshot(
        by_status=by_status,
        active=len(active),
        unassigned=sum(t.assignee is None for t in active),
        escalated=sum(t.is_escalated for t in active),
        blocked=by_status[S.BLOCKED],
        critical_or_high=sum(t.priority in URGENT for t in active),
        sla_breached=sum(t.age_hours > t.sla_target_hours for t in active),
        sla_at_risk=sum(
            t.sla_target_hours * SLA_AT_RISK_FRACTION < t.age_hours <= t.sla_target_hours for t in active
        ),
        awaiting_reporter=by_status[S.RESOLVED],
    )

def _attention_sort_key(t: TicketSummary):
    return (min(FLAG_RANK[f.kind] for f in t.flags), PRIORITY_RANK[t.priority], -t.age_hours)


# ---------- inside the date range ----------

async def _median_hours(db: AsyncSession, delta, where: list) -> tuple[float | None, int]:
    seconds = func.extract("epoch", delta)
    query = select(func.percentile_cont(0.5).within_group(seconds), func.count(seconds)).where(*where)
    median, count = (await db.execute(query)).one()
    return _hours(median), count

async def _timings(db: AsyncSession, where: list, start, end, previous_start) -> Timings:
    measures = {
        # (time from creation to ..., counted for tickets that ...)
        "acknowledge": (Incident.acknowledged_at, Incident.created_at),
        "assign": (Incident.assigned_at, Incident.created_at),
        "resolve": (Incident.resolved_at, Incident.resolved_at),
    }
    result = {}
    for name, (reached_at, range_column) in measures.items():
        delta = reached_at - Incident.created_at
        median, count = await _median_hours(db, delta, [*where, _in_range(range_column, start, end)])
        previous = None
        if previous_start is not None:
            previous, _ = await _median_hours(db, delta, [*where, _in_range(range_column, previous_start, start)])
        result[name] = Duration(median_hours=median, count=count, previous_median_hours=previous)
    return Timings(**result)

def _sla_target_seconds():
    # explicit comparisons, so the enum is bound through the column's type (case(value=...) sends the raw value)
    return case(*((Incident.priority == p, hours * 3600) for p, hours in SLA_TARGET_HOURS.items()))

async def _sla_rows(db: AsyncSession, where: list, start, end) -> dict[IncidentPriority, tuple[int, int]]:
    seconds = func.extract("epoch", Incident.resolved_at - Incident.created_at)
    query = (
        select(Incident.priority, func.count(), func.count().filter(seconds <= _sla_target_seconds()))
        .where(*where, _in_range(Incident.resolved_at, start, end))
        .group_by(Incident.priority)
    )
    return {priority: (resolved, met) for priority, resolved, met in (await db.execute(query)).all()}

async def _sla(db: AsyncSession, where: list, start, end, previous_start) -> SlaStats:
    rows = await _sla_rows(db, where, start, end)
    resolved = sum(r for r, _ in rows.values())
    met = sum(m for _, m in rows.values())
    previous_pct = None
    if previous_start is not None:
        previous = await _sla_rows(db, where, previous_start, start)
        previous_pct = _pct(sum(m for _, m in previous.values()), sum(r for r, _ in previous.values()))
    return SlaStats(
        resolved=resolved,
        met=met,
        met_pct=_pct(met, resolved),
        previous_met_pct=previous_pct,
        by_priority=[
            SlaPriorityRow(priority=p, target_hours=target, resolved=rows.get(p, (0, 0))[0], met=rows.get(p, (0, 0))[1])
            for p, target in SLA_TARGET_HOURS.items()
        ],
    )

async def _counts_by(db: AsyncSession, column, where: list) -> list[CountItem]:
    query = select(column, func.count()).where(*where).group_by(column).order_by(func.count().desc())
    return [CountItem(key=value.value, count=count) for value, count in (await db.execute(query)).all()]

async def _trend(db: AsyncSession, where: list, start, end, tz: str) -> tuple[str, list[TrendPoint]]:
    if start is None:
        first = await db.scalar(select(func.min(Incident.created_at)).where(*where))
        start = first or end
    bucket = "day" if end - start <= timedelta(days=DAILY_TREND_MAX_DAYS) else "week"

    counts: dict[float, dict[str, int]] = {}
    for key, column in (("created", Incident.created_at), ("resolved", Incident.resolved_at)):
        truncated = func.date_trunc(bucket, column, tz)
        query = (
            select(truncated, func.count())
            .where(*where, _in_range(column, start, end))
            .group_by(truncated)
        )
        for at, count in (await db.execute(query)).all():
            counts.setdefault(at.timestamp(), {})[key] = count

    # every bucket from start to end, so days with nothing still show as 0 on the chart
    zone = ZoneInfo(tz)
    cursor = start.astimezone(zone).replace(hour=0, minute=0, second=0, microsecond=0)
    if bucket == "week":
        cursor -= timedelta(days=cursor.weekday())  # Postgres weeks start on Monday
    step = timedelta(days=1 if bucket == "day" else 7)
    points = []
    while cursor < end:
        c = counts.get(cursor.timestamp(), {})
        points.append(TrendPoint(bucket=cursor, created=c.get("created", 0), resolved=c.get("resolved", 0)))
        cursor = (cursor + step).replace(tzinfo=zone)  # wall-clock step, stays on local midnight across DST
    return bucket, points

async def _hotspots(db: AsyncSession, where: list) -> Hotspots:
    active = func.count().filter(Incident.status.in_(ACTIVE))

    # every level is joined through its building + facility, so rows can say which campus they're on
    async def ranked(id_column, label, *joins) -> list[HotspotItem]:
        def joined(query):
            for target, on in (building_join, facility_join, *joins):
                query = query.join(target, on)
            return query

        query = (
            joined(select(id_column, label, Building.id, Facility.name, func.count(), active).select_from(Incident))
            .where(*where, id_column.is_not(None))
            .group_by(id_column, label, Building.id, Facility.name)
            .order_by(func.count().desc(), label)
            .limit(HOTSPOT_LIMIT)
        )
        rows = (await db.execute(query)).all()

        # the most reported category at each of those locations -- what keeps going wrong there
        top: dict[int, tuple] = {}
        if rows:
            by_category = (
                joined(select(id_column, Incident.category, func.count()).select_from(Incident))
                .where(*where, id_column.in_([row[0] for row in rows]))
                .group_by(id_column, Incident.category)
                .order_by(func.count().desc(), Incident.category)
            )
            for location_id, category, n in (await db.execute(by_category)).all():
                top.setdefault(location_id, (category, n))  # first row per location is its biggest
        return [
            HotspotItem(
                id=i, label=text, building_id=b, facility=f, count=n, active=a,
                top_category=top[i][0], top_category_count=top[i][1], recurring=top[i][1] >= RECURRING_MIN,
            )
            for i, text, b, f, n, a in rows
        ]

    building_join = (Building, Building.id == Incident.building_id)
    facility_join = (Facility, Facility.id == Building.facility_id)
    floor_join = (Floor, Floor.id == Incident.floor_id)
    floor_label = Building.name + literal(" · ") + Floor.name
    return Hotspots(
        buildings=await ranked(Building.id, Building.name),
        floors=await ranked(Floor.id, floor_label, floor_join),
        seats=await ranked(Seat.id, floor_label + literal(" · ") + Seat.code, floor_join, (Seat, Seat.id == Incident.seat_id)),
    )

async def _period(db: AsyncSession, where: list, start, end, previous_start, tz: str) -> PeriodStats:
    created_in = [*where, _in_range(Incident.created_at, start, end)]

    async def count_where(*conditions) -> int:
        return await db.scalar(select(func.count()).select_from(Incident).where(*conditions))

    bucket, trend = await _trend(db, where, start, end, tz)
    return PeriodStats(
        created=await count_where(*created_in),
        resolved=await count_where(*where, _in_range(Incident.resolved_at, start, end)),
        closed=await count_where(*where, _in_range(Incident.closed_at, start, end)),
        previous_created=(
            await count_where(*where, _in_range(Incident.created_at, previous_start, start))
            if previous_start is not None else None
        ),
        by_priority=await _counts_by(db, Incident.priority, created_in),
        by_category=await _counts_by(db, Incident.category, created_in),
        timings=await _timings(db, where, start, end, previous_start),
        sla=await _sla(db, where, start, end, previous_start),
        trend_bucket=bucket,
        trend=trend,
        hotspots=await _hotspots(db, created_in),
    )


# ---------- engineer workload (not limited to the caller's tickets) ----------

async def _workload(db: AsyncSession, start, end, facility_ids: list[int] | None) -> list[EngineerLoad]:
    load = (
        select(
            Incident.assignee_id.label("user_id"),
            func.count().filter(Incident.status.in_(ACTIVE)).label("active"),
            func.count().filter(Incident.status == S.BLOCKED).label("blocked"),
            func.count().filter(Incident.status.in_(ACTIVE), Incident.priority.in_(URGENT)).label("urgent"),
            func.count().filter(_in_range(Incident.resolved_at, start, end)).label("resolved"),
        )
        .where(Incident.assignee_id.is_not(None))
        .group_by(Incident.assignee_id)
        .subquery()
    )
    query = (
        select(EngineerProfile, load.c.active, load.c.blocked, load.c.urgent, load.c.resolved)
        .join(User, User.id == EngineerProfile.user_id)
        .outerjoin(load, load.c.user_id == EngineerProfile.user_id)
        .where(User.is_active.is_(True))
    )
    if facility_ids is not None:
        query = query.where(users_in(facility_ids))
    rows = [
        EngineerLoad(
            user_id=profile.user_id,
            display_name=profile.display_name,
            facility_id=profile.facility_id,
            specialty=profile.specialty,
            is_available=profile.is_available,
            max_open_tickets=profile.max_open_tickets,
            active=active or 0,
            blocked=blocked or 0,
            critical_or_high=urgent or 0,
            resolved_in_range=resolved or 0,
            load_pct=round(100 * (active or 0) / profile.max_open_tickets, 1),
        )
        for profile, active, blocked, urgent, resolved in (await db.execute(query)).all()
    ]
    return sorted(rows, key=lambda r: (-r.load_pct, r.display_name))


@router.get("/dashboard", response_model=Dashboard)
async def get_dashboard(
    start: datetime | None = Query(default=None, description="range start (inclusive). omit for all time"),
    end: datetime | None = Query(default=None, description="range end (exclusive). defaults to now"),
    facility_id: list[int] | None = Query(default=None, description="admins: limit to these facilities (default all)"),
    building_id: int | None = None,
    tz: str = Query(default="UTC", description="IANA time zone used to group the trend by day/week"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dashboard:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise _bad_request(f"Unknown time zone '{tz}'")

    now = datetime.now(timezone.utc)
    start, end = _as_utc(start), _as_utc(end) or now
    if start is not None and start >= end:
        raise _bad_request("start must be before end")
    # same-length window right before this one, to show whether things got better or worse
    previous_start = start - (end - start) if start is not None else None

    scope, scope_filter = _scope_for(current_user)
    where = [scope_filter]
    # admins may narrow to some facilities. engineers/employees are already limited to their own tickets,
    # and their team workload to their own facility
    facility_ids = visible_facility_ids(current_user, facility_id)
    if scope == DashboardScope.ALL and facility_ids is not None:
        where.append(incidents_in(facility_ids))
    if building_id is not None:
        where.append(Incident.building_id == building_id)

    tickets = await _live_tickets(db, where, scope, now)
    active = [t for t in tickets if t.status in ACTIVE]
    silent = sum(any(f.kind == AttentionKind.SILENT for f in t.flags) for t in active)
    attention = sorted((t for t in tickets if t.flags), key=_attention_sort_key)[:ATTENTION_LIMIT]

    return Dashboard(
        scope=scope,
        range=DashboardRange(start=start, end=end, previous_start=previous_start),
        facility_ids=facility_ids if scope == DashboardScope.ALL else None,
        building_id=building_id,
        sla_targets_hours=SLA_TARGET_HOURS,
        current=_snapshot(tickets),
        attention=attention,
        my_tickets=(
            sorted(tickets, key=lambda t: (t.status != S.RESOLVED, -t.last_update_at.timestamp()))
            if scope == DashboardScope.REPORTED else None
        ),
        period=await _period(db, where, start, end, previous_start, tz),
        communication=Communication(
            silent_after_days=SILENT_AFTER_DAYS,
            active=len(active),
            updated_recently=len(active) - silent,
            updated_recently_pct=_pct(len(active) - silent, len(active)),
        ),
        workload=await _workload(db, start, end, facility_ids) if scope != DashboardScope.REPORTED else None,
    )
