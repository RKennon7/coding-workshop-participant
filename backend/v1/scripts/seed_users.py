import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import User, UserRole
from app.security import hash_password

TEST_USERS = [
    ("admin", "testadmin@acme.inc", UserRole.FACILITY_ADMIN),
    ("engineer", "testengineer@acme.inc", UserRole.ENGINEER),
    ("employee", "testemployee@acme.inc", UserRole.EMPLOYEE),
]

# well-known password for seeded accounts, used locally only. in AWS, init_db passes a random or
# operator-chosen password instead so the deployed app never has guessable logins (see scripts/init_db.py)
DEFAULT_PASSWORD = "password123"

# Safe to re-run: only creates test users whose email doesn't exist yet
async def seed_users(password_hash: str | None = None) -> None:
    password_hash = password_hash or hash_password(DEFAULT_PASSWORD)
    async with AsyncSessionLocal() as session:
        existing = set(await session.scalars(select(User.email).where(User.email.in_([email for _, email, _ in TEST_USERS]))))
        missing = [(username, email, role) for username, email, role in TEST_USERS if email not in existing]
        session.add_all([
            User(username=username, email=email, password_hash=password_hash, role=role)
            for username, email, role in missing
        ])
        await session.commit()
        print(f"Seeded {len(missing)} test users ({len(existing)} already existed).")

if __name__ == "__main__":
    asyncio.run(seed_users())
