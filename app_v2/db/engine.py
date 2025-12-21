from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app_v2.core.config import Settings
from app_v2.db.models import Base
import logging

logger = logging.getLogger(__name__)

# Engine global (singleton)
_engine = None
_session_maker = None

def get_engine(settings: Settings):
    global _engine
    if _engine is None:
        # CRITIQUE : ?mode=wal est déjà actif dans ta DB, on le garde
        # check_same_thread=False nécessaire pour async
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.log_level == "DEBUG",
            pool_pre_ping=True,
            pool_recycle=3600,
            poolclass=NullPool,  # Pas de pool pour SQLite
            connect_args={"check_same_thread": False},
        )
        logger.info(f"✓ Engine créé : {settings.database_url}")
    return _engine

def get_session_maker(settings: Settings):
    global _session_maker
    if _session_maker is None:
        engine = get_engine(settings)
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_maker

async def get_db(settings: Settings):
    """Dependency injection pour FastAPI"""
    session_maker = get_session_maker(settings)
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db(settings: Settings):
    """Initialise les tables (crée seulement si n'existent pas)"""
    engine = get_engine(settings)
    async with engine.begin() as conn:
        # NE PAS drop les tables existantes
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✓ Tables DB initialisées")

async def close_db():
    """Ferme proprement l'engine"""
    global _engine, _session_maker
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("✓ Engine DB fermé")
