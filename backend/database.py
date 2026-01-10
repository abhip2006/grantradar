"""
GrantRadar Database Connection Setup
Provides async and sync database engines with connection pooling.
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import settings
from backend.models import Base

# =============================================================================
# Async Engine and Session (for FastAPI)
# =============================================================================

async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields an async database session and ensures proper cleanup.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async database sessions.

    Use this for manual session management outside of FastAPI routes.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(select(Grant))
            grants = result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Sync Engine and Session (for Celery workers)
# =============================================================================

sync_engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


def get_sync_db() -> Session:
    """
    Get a synchronous database session for Celery workers.

    Returns a session that must be manually closed.

    Usage:
        db = get_sync_db()
        try:
            grants = db.query(Grant).all()
        finally:
            db.close()
    """
    return SyncSessionLocal()


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    Context manager for synchronous database sessions.

    Use this for Celery tasks that need automatic session management.

    Usage:
        with get_sync_session() as session:
            grants = session.query(Grant).all()
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# Database Initialization
# =============================================================================


async def init_db() -> None:
    """
    Initialize the database by creating all tables.

    Note: In production, use Alembic migrations instead.
    This is primarily for development and testing.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close all database connections.

    Call this during application shutdown.
    """
    await async_engine.dispose()


def close_sync_db() -> None:
    """
    Close synchronous database connections.

    Call this when shutting down Celery workers.
    """
    sync_engine.dispose()


# =============================================================================
# Health Check
# =============================================================================


async def check_db_connection() -> dict[str, Any]:
    """
    Check database connectivity for health checks.

    Returns:
        dict with connection status and details
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "database": "connected",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }
