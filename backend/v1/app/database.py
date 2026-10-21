from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = settings.database_url

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.is_local,  # SQL logging locally only; keeps CloudWatch logs clean
    connect_args={} if settings.is_local else {"ssl": "require"},  # Aurora requires SSL
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)