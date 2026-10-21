import asyncio

from sqlalchemy import text

from app.models import Base
from app.database import engine

# create_all only adds missing tables, it never alters existing ones -- small column changes go here.
# each statement must be safe to re-run on every deploy.
SCHEMA_PATCHES = [
    # invited users have no password until they register
    "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
]

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in SCHEMA_PATCHES:
            await conn.execute(text(statement))

if __name__ == "__main__":
    asyncio.run(create_tables())