"""Create the database schema: every table from the ORM models, plus small hand-written patches.

Called by scripts/init_db.py on every deployment (and runnable alone: python -m scripts.create_tables
from backend/v1). There is no migration tool (e.g. Alembic) in this project, so SCHEMA_PATCHES is
how columns get added/changed on databases that already exist.
"""
import asyncio

from sqlalchemy import text

from app.models import Base
from app.database import engine

# create_all only adds missing tables, it never alters existing ones -- small column changes go here.
# each statement must be safe to re-run on every deploy.
SCHEMA_PATCHES = [
    # invited users have no password until they register
    "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
    # users belong to a facility (campus)
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS facility_id INTEGER REFERENCES facilities(id)",
    "CREATE INDEX IF NOT EXISTS ix_users_facility_id ON users (facility_id)",
    # databases created before facilities were per-user: put existing engineers/employees in the oldest facility.
    # a no-op once everyone has one (the API won't create engineers/employees without a facility)
    # raw SQL uses the enum member names ('ENGINEER'), which is what SQLAlchemy stores, not the values ('Engineer')
    """
    UPDATE users SET facility_id = (SELECT id FROM facilities ORDER BY id LIMIT 1)
    WHERE facility_id IS NULL AND role IN ('ENGINEER', 'EMPLOYEE')
    """,
]

async def create_tables():
    """Create missing tables, then apply SCHEMA_PATCHES, all in one transaction (engine.begin commits at the end)."""
    # create_all is a sync API, so it runs through run_sync on the async connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in SCHEMA_PATCHES:
            await conn.execute(text(statement))

if __name__ == "__main__":
    asyncio.run(create_tables())