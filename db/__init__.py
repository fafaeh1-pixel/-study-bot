from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from db.models import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False)

_SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db():
    async with _SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """یه بار اول برنامه صدا بزن تا جداول ساخته بشن."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)