import asyncio
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import (
    Building,
    EngineerProfile,
    Facility,
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
from app.security import hash_password
from scripts.seed_users import DEFAULT_PASSWORD

# Seeds a small but realistic dataset for dashboards/reporting. Safe to re-run: it skips if the
# sample facility already exists, and reuses any users already created by seed_users.py.
# Run from backend/v1:  python -m scripts.seed_sample_data

rng = random.Random(42)  # fixed seed so every run produces the same dataset
NOW = datetime.now(timezone.utc)

FACILITY_NAME = "ACME HQ Campus"
BUILDINGS = {"North Tower": ("NT", 3), "South Annex": ("SA", 2)}  # name -> (seat prefix, floor count)
SEATS_PER_FLOOR = 4
HOTSPOT_FLOOR = 2  # North Tower Floor 3 -- gets a disproportionate share of incidents
HOTSPOT_SEAT = 1   # NT-3-02 -- the desk that keeps breaking

ADMINS = [("admin", "testadmin@acme.inc")]
ENGINEERS = [
    # username, email, display name, specialty, available, workload weight
    ("engineer", "testengineer@acme.inc", "Test Engineer", IncidentCategory.HARDWARE, True, 4),
    ("jordan.lee", "jordan.lee@acme.inc", "Jordan Lee", IncidentCategory.NETWORK, True, 3),
    ("morgan.patel", "morgan.patel@acme.inc", "Morgan Patel", IncidentCategory.HVAC, True, 3),
    ("sam.garcia", "sam.garcia@acme.inc", "Sam Garcia", IncidentCategory.ELECTRICAL, False, 1),  # on leave
]
EMPLOYEES = [
    # username, email, reporting weight
    ("employee", "testemployee@acme.inc", 3),
    ("alex.kim", "alex.kim@acme.inc", 4),
    ("casey.nguyen", "casey.nguyen@acme.inc", 2),
    ("riley.brooks", "riley.brooks@acme.inc", 2),
    ("taylor.wong", "taylor.wong@acme.inc", 1),
    ("jamie.ortiz", "jamie.ortiz@acme.inc", 1),
]

# fixed status mix so every workflow column has data
STATUS_COUNTS = {
    IncidentStatus.OPEN: 8,
    IncidentStatus.IN_PROGRESS: 8,
    IncidentStatus.BLOCKED: 5,
    IncidentStatus.RESOLVED: 9,
    IncidentStatus.CLOSED: 12,
}
ACTIVE_STATUSES = {IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS, IncidentStatus.BLOCKED}
DONE_STATUSES = {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
# how long each incident has sat since its last activity, by status
IDLE_DAYS = {
    IncidentStatus.OPEN: (0.05, 2),
    IncidentStatus.IN_PROGRESS: (0.1, 3),
    IncidentStatus.BLOCKED: (0.5, 6),
    IncidentStatus.RESOLVED: (0.2, 4),
    IncidentStatus.CLOSED: (1, 25),
}

PRIORITY_WEIGHTS = {
    IncidentPriority.LOW: 3,
    IncidentPriority.MEDIUM: 5,
    IncidentPriority.HIGH: 3,
    IncidentPriority.CRITICAL: 1,
}
# multiplier on acknowledge/assign/resolve times -- urgent tickets get handled faster
RESPONSE_SPEED = {
    IncidentPriority.LOW: 1.5,
    IncidentPriority.MEDIUM: 1.0,
    IncidentPriority.HIGH: 0.5,
    IncidentPriority.CRITICAL: 0.2,
}

CATEGORY_WEIGHTS = {
    IncidentCategory.NETWORK: 6,
    IncidentCategory.HVAC: 5,
    IncidentCategory.HARDWARE: 5,
    IncidentCategory.ELECTRICAL: 3,
    IncidentCategory.FURNITURE: 3,
    IncidentCategory.AV_EQUIPMENT: 2,
    IncidentCategory.PLUMBING: 2,
    IncidentCategory.SECURITY_ACCESS: 2,
    IncidentCategory.CLEANING: 1,
    IncidentCategory.OTHER: 1,
}
# categories that relate to an area of the floor rather than a specific desk
AREA_CATEGORIES = {
    IncidentCategory.PLUMBING,
    IncidentCategory.CLEANING,
    IncidentCategory.SECURITY_ACCESS,
    IncidentCategory.AV_EQUIPMENT,
}
TEMPLATES = {
    IncidentCategory.NETWORK: [
        ("Wi-Fi keeps dropping", "Laptop disconnects from ACME-Corp Wi-Fi every 10-15 minutes."),
        ("Ethernet port not working", "Wall ethernet port at my desk shows no link light."),
        ("Very slow network", "Pages and file shares are taking over a minute to load."),
    ],
    IncidentCategory.HVAC: [
        ("Office too hot", "Temperature around my desk has been above 28C all afternoon."),
        ("AC vent leaking", "Water is dripping from the ceiling vent above the desk area."),
        ("Area too cold", "Air vent is blasting cold air directly onto the desks."),
    ],
    IncidentCategory.HARDWARE: [
        ("Monitor won't turn on", "External monitor has no power light, tried a different cable."),
        ("Docking station not detecting laptop", "Dock doesn't charge or show displays when laptop is connected."),
        ("Keyboard missing keys", "Several keys on the shared desk keyboard are broken."),
    ],
    IncidentCategory.ELECTRICAL: [
        ("Desk power outlet dead", "None of the outlets under the desk are providing power."),
        ("Flickering overhead lights", "Lights above this row flicker constantly, causing headaches."),
    ],
    IncidentCategory.FURNITURE: [
        ("Broken chair", "Chair won't stay at height and sinks to the lowest setting."),
        ("Standing desk stuck", "Standing desk motor makes a noise but won't move up or down."),
    ],
    IncidentCategory.AV_EQUIPMENT: [
        ("Conference room projector not working", "Projector shows 'no signal' with any HDMI input."),
        ("Meeting room speakerphone has no audio", "Remote attendees can't hear anyone in the room."),
    ],
    IncidentCategory.PLUMBING: [
        ("Restroom sink clogged", "Sink in the restroom near the elevators is not draining."),
        ("Water fountain not working", "Water fountain by the kitchen has no pressure."),
    ],
    IncidentCategory.SECURITY_ACCESS: [
        ("Badge reader not working", "Badge reader at the floor entrance doesn't respond to any badge."),
        ("Door not locking", "Side stairwell door doesn't latch closed."),
    ],
    IncidentCategory.CLEANING: [
        ("Spill in kitchen area", "Large coffee spill on the kitchen floor, slippery."),
    ],
    IncidentCategory.OTHER: [
        ("Strange smell near desks", "There's a burning smell coming from somewhere in this area."),
    ],
}

BLOCKED_REASONS = [
    "Waiting on a replacement part from the vendor",
    "Needs contractor access to the ceiling space",
    "Waiting for the employee to be available at their desk",
    "Pending approval from building management",
    "Requires a network change window this weekend",
]
ESCALATION_REASONS = [
    "Issue is preventing the whole team from working",
    "No response after more than a day",
    "Possible safety hazard",
    "Client meeting in this room tomorrow",
]
PICKUP_NOTES = [
    "Picked this up, heading over to take a look.",
    "Thanks for reporting, I'm investigating now and will update shortly.",
    "On it -- will update this ticket by end of day.",
]
RESOLUTION_NOTES = [
    "Replaced the faulty component, everything is working now.",
    "Fixed -- please reopen if you see the issue again.",
    "Resolved after a reset and reconfiguration. Let us know if it recurs.",
]
INTERNAL_NOTES = [
    "Third report from this area this month, might need a bigger fix.",
    "Vendor warranty covers this, logged a claim.",
    "Check with building management about the recurring cause.",
]
FOLLOW_UP_NOTES = [
    "Any update on this? It's still affecting my work.",
    "Still seeing this issue today.",
]


def hours(lo: float, hi: float) -> timedelta:
    return timedelta(hours=rng.uniform(lo, hi))


async def get_or_create_user(session, username: str, email: str, role: UserRole, password_hash: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(username=username, email=email, password_hash=password_hash, role=role)
        session.add(user)
    return user


def build_locations() -> tuple[Facility, list[tuple[Building, Floor, list[Seat]]]]:
    facility = Facility(name=FACILITY_NAME, address="100 Main St, Springfield")
    locations = []
    for building_name, (prefix, floor_count) in BUILDINGS.items():
        building = Building(name=building_name)
        facility.buildings.append(building)
        for floor_number in range(1, floor_count + 1):
            seats = [Seat(code=f"{prefix}-{floor_number}-{n:02d}") for n in range(1, SEATS_PER_FLOOR + 1)]
            floor = Floor(name=f"Floor {floor_number}", seats=seats)
            building.floors.append(floor)
            locations.append((building, floor, seats))
    return facility, locations


def pick_location(category: IncidentCategory, locations) -> tuple[Building, Floor, Seat | None]:
    roll = rng.random()
    building, floor, seats = locations[HOTSPOT_FLOOR] if roll < 0.4 else rng.choice(locations)
    if category in AREA_CATEGORIES:
        return building, floor, None
    if roll < 0.25:
        return building, floor, seats[HOTSPOT_SEAT]
    return building, floor, rng.choice(seats) if rng.random() < 0.7 else None


def pick_engineer(category: IncidentCategory, engineers, available_only: bool) -> User:
    pool = [(user, profile, weight) for user, profile, weight in engineers if profile.is_available or not available_only]
    specialists = [user for user, profile, _ in pool if profile.specialty == category]
    if specialists and rng.random() < 0.6:
        return rng.choice(specialists)
    return rng.choices([user for user, _, _ in pool], weights=[weight for _, _, weight in pool])[0]


def build_incident(status: IncidentStatus, admin: User, engineers, employees, locations) -> Incident:
    category = rng.choices(list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()))[0]
    title, description = rng.choice(TEMPLATES[category])
    priority = rng.choices(list(PRIORITY_WEIGHTS), weights=list(PRIORITY_WEIGHTS.values()))[0]
    building, floor, seat = pick_location(category, locations)
    reporter = rng.choices([user for user, _ in employees], weights=[weight for _, weight in employees])[0]

    escalation_reason = None
    if status in ACTIVE_STATUSES and rng.random() < 0.3:
        escalation_reason = rng.choice(ESCALATION_REASONS)
        priority = rng.choice([IncidentPriority.HIGH, IncidentPriority.CRITICAL])
    speed = RESPONSE_SPEED[priority]

    # build the timeline as offsets from creation, then anchor it to real dates at the end
    t = timedelta(0)
    history = [(t, None, IncidentStatus.OPEN, reporter, None)]  # (offset, from, to, changed_by, reason)
    notes = []  # (offset, author, body, is_internal)
    acknowledged = assigned = resolved = closed = None
    engineer = None
    blocked_reason = None

    def move(to_status: IncidentStatus, by: User, reason: str | None = None) -> None:
        history.append((t, history[-1][2], to_status, by, reason))

    if escalation_reason:
        notes.append((hours(0.5, 4), reporter, f"Requesting escalation: {escalation_reason}.", False))

    # open tickets are a mix of untouched, acknowledged, and assigned-but-not-started
    if status != IncidentStatus.OPEN or rng.random() < 0.5:
        t += hours(0.2, 8) * speed
        acknowledged = t
        if status != IncidentStatus.OPEN or rng.random() < 0.5:
            t += hours(0.5, 24) * speed
            assigned = t
            engineer = pick_engineer(category, engineers, available_only=status in ACTIVE_STATUSES)

    if status != IncidentStatus.OPEN:
        t += hours(0.5, 6)
        move(IncidentStatus.IN_PROGRESS, engineer)
        if rng.random() < 0.75:  # not every engineer keeps the reporter informed
            notes.append((t, engineer, rng.choice(PICKUP_NOTES), False))

        # all blocked tickets, plus some finished ones that were blocked along the way
        if status == IncidentStatus.BLOCKED or (status in DONE_STATUSES and rng.random() < 0.25):
            t += hours(2, 48)
            reason = rng.choice(BLOCKED_REASONS)
            move(IncidentStatus.BLOCKED, engineer, reason)
            notes.append((t, engineer, f"Putting this on hold: {reason.lower()}.", False))
            if status == IncidentStatus.BLOCKED:
                blocked_reason = reason
            else:
                t += hours(12, 72)
                move(IncidentStatus.IN_PROGRESS, engineer, "Blocker cleared")

        if status in DONE_STATUSES:
            t += hours(2, 72) * speed
            move(IncidentStatus.RESOLVED, engineer)
            resolved = t
            notes.append((t, engineer, rng.choice(RESOLUTION_NOTES), False))

        if status == IncidentStatus.CLOSED:
            t += hours(4, 72)
            closer = rng.choice([reporter, admin])
            move(IncidentStatus.CLOSED, closer, "Confirmed fixed" if closer is reporter else "Auto-closed after no response")
            closed = t

    if engineer and rng.random() < 0.25:
        notes.append((t, engineer, rng.choice(INTERNAL_NOTES), True))
    if status in ACTIVE_STATUSES and rng.random() < 0.35:
        notes.append((t + hours(1, 12), reporter, rng.choice(FOLLOW_UP_NOTES), False))

    last_activity = max([t] + [offset for offset, *_ in notes])
    created = NOW - last_activity - timedelta(days=rng.uniform(*IDLE_DAYS[status]))

    def at(offset: timedelta | None) -> datetime | None:
        return created + offset if offset is not None else None

    return Incident(
        title=title,
        description=description,
        category=category,
        priority=priority,
        status=status,
        blocked_reason=blocked_reason,
        is_escalated=escalation_reason is not None,
        escalation_reason=escalation_reason,
        reporter_id=reporter.id,
        assignee_id=engineer.id if engineer else None,
        building_id=building.id,
        floor_id=floor.id if floor else None,
        seat_id=seat.id if seat else None,
        created_at=created,
        updated_at=at(last_activity),
        acknowledged_at=at(acknowledged),
        assigned_at=at(assigned),
        resolved_at=at(resolved),
        closed_at=at(closed),
        status_history=[
            IncidentStatusHistory(from_status=from_status, to_status=to_status, changed_by_id=by.id, reason=reason, changed_at=at(offset))
            for offset, from_status, to_status, by, reason in history
        ],
        notes=[
            IncidentNote(author_id=author.id, body=body, is_internal=is_internal, created_at=at(offset), updated_at=at(offset))
            for offset, author, body, is_internal in sorted(notes, key=lambda n: n[0])
        ],
    )


async def seed_sample_data(password_hash: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        if await session.scalar(select(Facility).where(Facility.name == FACILITY_NAME)):
            print(f"'{FACILITY_NAME}' already exists, skipping sample data.")
            return

        password_hash = password_hash or hash_password(DEFAULT_PASSWORD)
        admin = await get_or_create_user(session, *ADMINS[0], UserRole.FACILITY_ADMIN, password_hash)
        engineer_users = [
            await get_or_create_user(session, username, email, UserRole.ENGINEER, password_hash)
            for username, email, *_ in ENGINEERS
        ]
        employees = [
            (await get_or_create_user(session, username, email, UserRole.EMPLOYEE, password_hash), weight)
            for username, email, weight in EMPLOYEES
        ]
        facility, locations = build_locations()
        session.add(facility)
        await session.flush()  # assign ids so incidents can reference users and locations

        engineers = []
        for user, (_, _, display_name, specialty, available, weight) in zip(engineer_users, ENGINEERS):
            profile = await session.scalar(select(EngineerProfile).where(EngineerProfile.user_id == user.id))
            if profile is None:
                profile = EngineerProfile(user_id=user.id, display_name=display_name, specialty=specialty, is_available=available)
                session.add(profile)
            engineers.append((user, profile, weight))

        statuses = [status for status, count in STATUS_COUNTS.items() for _ in range(count)]
        rng.shuffle(statuses)
        incidents = [build_incident(status, admin, engineers, employees, locations) for status in statuses]
        session.add_all(incidents)
        await session.commit()

        print(
            f"Seeded 1 facility, {len(BUILDINGS)} buildings, {len(locations)} floors, "
            f"{len(locations) * SEATS_PER_FLOOR} seats, {len(engineers)} engineers, {len(employees)} employees, "
            f"{len(incidents)} incidents, {sum(len(i.notes) for i in incidents)} notes."
        )


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
