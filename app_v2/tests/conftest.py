"""
Shared test fixtures and configuration for app_v2 tests.

Provides:
- Test database with in-memory SQLite
- Test FastAPI app instance
- Mock Redis client
- Database session fixtures
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from fastapi.testclient import TestClient
import redis.asyncio as redis

from app_v2.main import app
from app_v2.core.config import Settings
from app_v2.db.models import Base


# =========================================================================
# TEST SETTINGS
# =========================================================================

@pytest.fixture(scope="session")
def test_settings():
    """Test configuration with in-memory database."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        api_key="test-api-key-12345",
        auth_encryption_key="test-encryption-key-12345",
        jwt_secret="test-jwt-secret-12345",
        # Rate limiting with low values for testing
        max_messages_per_day=10,
        max_messages_per_week=50,
        max_messages_per_execution=5,
    )


# =========================================================================
# DATABASE FIXTURES
# =========================================================================

@pytest_asyncio.fixture
async def test_db_engine(test_settings):
    """Create test database engine with in-memory SQLite."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_db_session_fresh(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database session (clean state)."""
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


# =========================================================================
# REDIS FIXTURES
# =========================================================================

@pytest_asyncio.fixture
async def test_redis_mock():
    """Mock Redis client for testing (using fakeredis if available)."""
    try:
        import fakeredis.aioredis
        redis_client = fakeredis.aioredis.FakeRedis()
        yield redis_client
        await redis_client.flushdb()
    except ImportError:
        # Fallback: skip Redis tests if fakeredis not available
        pytest.skip("fakeredis not installed")


# =========================================================================
# API FIXTURES
# =========================================================================

@pytest.fixture
def test_client():
    """Test client for FastAPI app."""
    return TestClient(app)


# =========================================================================
# HELPER FIXTURES
# =========================================================================

@pytest_asyncio.fixture
async def populated_db(test_db_session):
    """Create database with sample data."""
    from app_v2.db.models import Contact, Interaction
    from datetime import date, datetime, timezone

    # Create test contacts
    contacts = [
        Contact(
            name="Alice Birthday",
            profile_url="https://linkedin.com/in/alice",
            birth_date=date(1990, 1, 15),
            status="new",
        ),
        Contact(
            name="Bob Birthday",
            profile_url="https://linkedin.com/in/bob",
            birth_date=date(1985, 3, 20),
            status="visited",
        ),
        Contact(
            name="Charlie Birthday",
            profile_url="https://linkedin.com/in/charlie",
            birth_date=date(1992, 12, 25),
            status="contacted",
        ),
    ]

    for contact in contacts:
        test_db_session.add(contact)

    await test_db_session.flush()

    # Create some interactions
    interactions = [
        Interaction(
            contact_id=contacts[0].id,
            type="birthday_sent",
            status="success",
            payload={"message_text": "Happy Birthday Alice!"},
        ),
        Interaction(
            contact_id=contacts[1].id,
            type="profile_visit",
            status="success",
            payload={"selector": "test_selector"},
        ),
    ]

    for interaction in interactions:
        test_db_session.add(interaction)

    await test_db_session.commit()

    return {
        "contacts": contacts,
        "interactions": interactions,
    }


# =========================================================================
# TEST MARKERS
# =========================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
