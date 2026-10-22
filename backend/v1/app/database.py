"""Async SQLAlchemy engine and session factory shared by the whole backend.

Routers get a session per request through dependencies.get_db; the scripts/ seeders open their own
with AsyncSessionLocal(). The engine is created once per process (one per warm Lambda container).
"""
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.is_local,  # SQL logging locally only; keeps CloudWatch logs clean
    connect_args={} if settings.is_local else {"ssl": "require"},  # Aurora requires SSL
)

# expire_on_commit=False: objects stay readable after commit. with async sessions an expired attribute
# would need a lazy reload, which isn't allowed outside an await and raises MissingGreenlet
# (e.g. when FastAPI serializes the response model after the route committed)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)