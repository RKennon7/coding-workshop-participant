"""Database initialization entry point: create tables, seed test users and (optionally) sample data.

Runs inside the Lambda via function.py ({"action": "init_db"}, sent by bin/init-database.sh) because the
database is only reachable from inside the VPC; locally it runs as a module (see the usage line below).
"""
import argparse
import asyncio
import secrets

from sqlalchemy import func, select, text

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.models import User
from app.security import hash_password, verify_password
from scripts.create_tables import create_tables
from scripts.seed_sample_data import ADMINS, EMPLOYEES, ENGINEERS, seed_sample_data
from scripts.seed_users import DEFAULT_PASSWORD, TEST_USERS, seed_users

# Creates any missing tables, then seeds test users and (optionally) sample data.
# Every step is idempotent, so this runs on every deployment -- see bin/init-database.sh.
# Run locally from backend/v1:  python -m scripts.init_db [--no-sample-data]

# arbitrary constant; a Postgres advisory lock on it stops two deploys initializing at once
INIT_DB_LOCK_ID = 4242_0001

# every account the seeders may create, so password rotation never touches real users
SEED_EMAILS = [email for _, email, _ in TEST_USERS] + [user[1] for user in ADMINS + ENGINEERS + EMPLOYEES]

# Seeded accounts (including a Facility Admin) must not have a guessable password once deployed.
# Locally they keep DEFAULT_PASSWORD for convenience. In AWS they get seed_password if the operator
# passed one (SEED_PASSWORD in bin/init-database.sh), otherwise a random one that is returned (never logged).
def resolve_seed_password(seed_password: str | None) -> tuple[str, bool]:
    """Return (password, generated) where generated is True if it was randomly created here."""
    if seed_password:
        return seed_password, False
    if settings.is_local:
        return DEFAULT_PASSWORD, False
    return secrets.token_urlsafe(12), True

# deployments seeded before this change still have DEFAULT_PASSWORD -- move them onto the new one
async def rotate_default_passwords(password_hash: str) -> int:
    """Give every seeded account still on DEFAULT_PASSWORD the new hash. Returns how many were changed.

    Accounts whose password was changed by a person are left alone. Slow-ish: one bcrypt check per account.
    """
    async with AsyncSessionLocal() as session:
        users = await session.scalars(
            select(User).where(User.email.in_(SEED_EMAILS), User.password_hash.is_not(None))
        )
        rotated = 0
        for user in users:
            if verify_password(DEFAULT_PASSWORD, user.password_hash):
                user.password_hash = password_hash
                rotated += 1
        await session.commit()
    return rotated

async def init_db(include_sample_data: bool = True, seed_password: str | None = None) -> dict:
    """Create/patch tables and seed data; safe to run repeatedly.

    Returns {"status": "ok", "sample_data": bool}, plus "seed_password" when a random password was
    generated and at least one account uses it -- that's the operator's only chance to see it
    (bin/init-database.sh prints the Lambda's response).
    """
    password, generated = resolve_seed_password(seed_password)
    password_hash = hash_password(password)  # one hash for every seeded account, so they can be counted below

    # session-level advisory lock held on its own connection for the whole run; released in finally
    # (and by Postgres automatically if the connection drops)
    async with engine.connect() as lock_conn:
        await lock_conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": INIT_DB_LOCK_ID})
        try:
            await create_tables()
            print("Tables created (existing tables are left unchanged).")
            await seed_users(password_hash)
            if include_sample_data:
                await seed_sample_data(password_hash)
            if password != DEFAULT_PASSWORD:
                rotated = await rotate_default_passwords(password_hash)
                print(f"Rotated {rotated} seeded accounts off the default password.")
            async with AsyncSessionLocal() as session:
                uses_password = await session.scalar(select(func.count()).where(User.password_hash == password_hash))
        finally:
            await lock_conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": INIT_DB_LOCK_ID})

    result = {"status": "ok", "sample_data": include_sample_data}
    # only report a generated password if some account actually got it this run
    if generated and uses_password:
        result["seed_password"] = password
    return result

# local CLI only: function.py calls init_db directly and must not dispose the shared engine
async def main(include_sample_data: bool) -> None:
    try:
        result = await init_db(include_sample_data)
        if "seed_password" in result:
            print(f"Generated password for the seeded accounts (save it, it is not stored anywhere): {result['seed_password']}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create tables and seed the database.")
    parser.add_argument("--no-sample-data", action="store_true", help="only create tables and test users")
    args = parser.parse_args()
    asyncio.run(main(include_sample_data=not args.no_sample_data))
