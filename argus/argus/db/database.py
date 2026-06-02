"""
Async database initialization and session management for ARGUS.
Uses SQLAlchemy with asyncpg for PostgreSQL async support.
"""
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from argus.config import settings


def _create_async_engine(url: str):
    engine_url = make_url(url)
    engine_kwargs = {
        "echo": settings.environment == "development",
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }

    if not engine_url.drivername.startswith("sqlite"):
        engine_kwargs.update({"pool_size": 20, "max_overflow": 0})

    return create_async_engine(url, **engine_kwargs)


engine = None
AsyncSessionLocal = None


def initialize_database(url: str | None = None):
    global engine, AsyncSessionLocal
    database_url = url or settings.database_url

    if engine is not None and AsyncSessionLocal is not None:
        current_url = str(engine.url)
        if url is None or current_url == database_url:
            return

    engine = _create_async_engine(database_url)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator providing database sessions for FastAPI dependency injection.
    Yields a session and ensures proper cleanup on exit.
    
    Yields:
        AsyncSession: Database session for a single request
    """
    initialize_database()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_db_and_tables() -> None:
    """
    Create all database tables based on SQLAlchemy ORM model definitions.
    Should be called once at application startup.
    Uses SQLAlchemy metadata.create_all() with async support.
    """
    # Import here to avoid circular imports
    from argus.core.registry.models import Base

    initialize_database()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            except Exception:
                pass
        return
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(
            f"Primary database connection failed ({e}). Falling back to local SQLite.",
        )

    fallback_url = "sqlite+aiosqlite:///./fallback_argus.db"
    initialize_database(fallback_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db_and_tables() -> None:
    """
    Drop all database tables. Used for testing and cleanup.
    WARNING: This destroys all data in the database.
    """
    from argus.core.registry.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
