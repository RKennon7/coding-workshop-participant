# test setup: the API runs in-process against a real Postgres database (analytics uses Postgres-only SQL,
# so SQLite isn't an option). connection settings come from backend/v1/.env or POSTGRES_* env vars as usual,
# but the database is always a separate *_test one, created on first run and wiped before every test.
import os

# must happen before anything imports app.config, which reads settings at import time
TEST_DB_NAME = os.environ.get("TEST_POSTGRES_NAME", "incident_platform_test")
if not TEST_DB_NAME.endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against '{TEST_DB_NAME}': the test database name must end in _test")
os.environ["POSTGRES_NAME"] = TEST_DB_NAME
os.environ["IS_LOCAL"] = "true"  # no TLS to the local database
os.environ["SECRET_KEY"] = "unit-test-secret-key-not-used-anywhere-else"
os.environ.pop("CORS_ORIGINS", None)

from dataclasses import dataclass

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.main import app
from app.models import (
    Base,
    Building,
    EngineerProfile,
    Facility,
    Floor,
    IncidentCategory,
    Seat,
    User,
    UserRole,
)
from app.security import hash_password

# the app logs every SQL statement when IS_LOCAL is true, which buries test output
engine.sync_engine.echo = False

# every seeded account shares this password. hashed once, bcrypt is deliberately slow
PASSWORD = "correct-horse-battery"
PASSWORD_HASH = hash_password(PASSWORD)


async def _ensure_test_database() -> None:
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_pass or None,
        database="postgres",
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()

@pytest.fixture(scope="session")
async def _schema():
    await _ensure_test_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

@pytest.fixture
async def _clean_db(_schema):
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

@pytest.fixture
async def client(_clean_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@dataclass
class World:
    """Two campuses with a full location tree, and one user per role/situation the tests need."""
    hq: Facility
    west: Facility
    tower: Building      # HQ
    annex: Building      # HQ
    hall: Building       # West
    tower_f1: Floor
    tower_f2: Floor
    annex_f1: Floor
    hall_f1: Floor
    tower_f1_seat: Seat
    tower_f2_seat: Seat
    hall_f1_seat: Seat
    admin: User          # Facility Admin, no home facility
    eng: User            # Engineer @ HQ
    eng2: User           # Engineer @ HQ
    west_eng: User       # Engineer @ West
    inactive_eng: User   # deactivated Engineer @ HQ
    emp: User            # Employee @ HQ
    emp2: User           # Employee @ HQ
    west_emp: User       # Employee @ West
    invited: User        # Employee @ HQ, created by an admin but hasn't registered yet
    eng_profile: EngineerProfile
    eng2_profile: EngineerProfile
    west_eng_profile: EngineerProfile

@pytest.fixture
async def world(_clean_db) -> World:
    async with AsyncSessionLocal() as db:
        hq = Facility(name="HQ Campus", address="1 Main St")
        west = Facility(name="West Campus")
        tower = Building(facility=hq, name="Tower")
        annex = Building(facility=hq, name="Annex")
        hall = Building(facility=west, name="Hall")
        tower_f1 = Floor(building=tower, name="Floor 1")
        tower_f2 = Floor(building=tower, name="Floor 2")
        annex_f1 = Floor(building=annex, name="Floor 1")
        hall_f1 = Floor(building=hall, name="Floor 1")
        tower_f1_seat = Seat(floor=tower_f1, code="T-1-01")
        tower_f2_seat = Seat(floor=tower_f2, code="T-2-01")
        hall_f1_seat = Seat(floor=hall_f1, code="H-1-01")
        db.add_all([hq, west])
        await db.flush()

        def user(username: str, role: UserRole, facility: Facility | None, **kwargs) -> User:
            kwargs.setdefault("password_hash", PASSWORD_HASH)
            return User(
                username=username, email=f"{username}@acme.inc", role=role,
                facility_id=facility.id if facility else None, **kwargs,
            )

        admin = user("admin", UserRole.FACILITY_ADMIN, None)
        eng = user("eng", UserRole.ENGINEER, hq)
        eng2 = user("eng2", UserRole.ENGINEER, hq)
        west_eng = user("westeng", UserRole.ENGINEER, west)
        inactive_eng = user("inactive", UserRole.ENGINEER, hq, is_active=False)
        emp = user("emp", UserRole.EMPLOYEE, hq)
        emp2 = user("emp2", UserRole.EMPLOYEE, hq)
        west_emp = user("westemp", UserRole.EMPLOYEE, west)
        invited = user("invited", UserRole.EMPLOYEE, hq, password_hash=None)
        db.add_all([admin, eng, eng2, west_eng, inactive_eng, emp, emp2, west_emp, invited])
        await db.flush()

        eng_profile = EngineerProfile(user_id=eng.id, display_name="Eng One", specialty=IncidentCategory.HVAC)
        eng2_profile = EngineerProfile(user_id=eng2.id, display_name="Eng Two", specialty=IncidentCategory.NETWORK)
        west_eng_profile = EngineerProfile(user_id=west_eng.id, display_name="West Eng")
        db.add_all([eng_profile, eng2_profile, west_eng_profile])
        await db.commit()

        return World(
            hq=hq, west=west, tower=tower, annex=annex, hall=hall,
            tower_f1=tower_f1, tower_f2=tower_f2, annex_f1=annex_f1, hall_f1=hall_f1,
            tower_f1_seat=tower_f1_seat, tower_f2_seat=tower_f2_seat, hall_f1_seat=hall_f1_seat,
            admin=admin, eng=eng, eng2=eng2, west_eng=west_eng, inactive_eng=inactive_eng,
            emp=emp, emp2=emp2, west_emp=west_emp, invited=invited,
            eng_profile=eng_profile, eng2_profile=eng2_profile, west_eng_profile=west_eng_profile,
        )
