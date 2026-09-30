from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# Engine/sessionmaker are created lazily and cached so that importing this
# module never opens a network connection (important for fast startup and so
# the app can boot even if the database is briefly unreachable).
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        is_sqlite = "sqlite" in str(settings.DATABASE_URL)
        if is_sqlite:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                future=True,
            )
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL,
                echo=False,
                pool_pre_ping=True,
                future=True,
                pool_recycle=60,
                pool_size=10,
                max_overflow=15,
                connect_args={
                    "prepared_statement_cache_size": 0,
                    "statement_cache_size": 0,
                    "command_timeout": 30,
                },
            )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional session.

    Commits on success, rolls back on error, always closes.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Dispose the engine's connection pool (called on shutdown)."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
