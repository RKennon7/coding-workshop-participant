import asyncio

from app.database import AsyncSessionLocal
from app.models import User, UserRole
from app.security import hash_password

async def seed_users() -> None:
    async with AsyncSessionLocal() as session:
        session.add_all([
            User(username="admin", email="testadmin@acme.inc", password_hash=hash_password("password123"), role=UserRole.FACILITY_ADMIN),
            User(username="engineer", email="testengineer@acme.inc", password_hash=hash_password("password123"), role=UserRole.ENGINEER),
            User(username="employee", email="testemployee@acme.inc", password_hash=hash_password("password123"), role=UserRole.EMPLOYEE),
        ])
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed_users())