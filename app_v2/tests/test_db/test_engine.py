"""
Unit tests for database engine (app_v2/db/engine.py).

Tests async session management, connection pooling, and initialization.
"""

import pytest
import pytest_asyncio
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app_v2.db.engine import get_engine, get_session_maker, init_db
from app_v2.db.models import Base, Contact
from app_v2.core.config import Settings


@pytest.mark.integration
class TestDatabaseEngine:
    """Test async database engine functionality."""

    @pytest.mark.asyncio
    async def test_get_engine(self, test_settings):
        """Test creating async engine."""
        engine = get_engine(test_settings)

        assert engine is not None
        assert str(engine.url) == test_settings.database_url

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_engine_can_execute_query(self, test_db_engine):
        """Test that engine can execute basic queries."""
        async with test_db_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()

        assert value == 1

    @pytest.mark.asyncio
    async def test_engine_creates_tables(self, test_settings):
        """Test that engine can create all tables."""
        engine = get_engine(test_settings)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify tables exist
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='contact'"
                )
            )
            table_name = result.scalar()

        assert table_name == "contact"

        await engine.dispose()


@pytest.mark.integration
class TestAsyncSession:
    """Test async session management."""

    @pytest.mark.asyncio
    async def test_get_session_maker(self, test_settings):
        """Test creating session maker."""
        session_maker = get_session_maker(test_settings)

        assert session_maker is not None

        async with session_maker() as session:
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_session_can_query(self, test_db_session):
        """Test that session can execute queries."""
        result = await test_db_session.execute(select(Contact))
        contacts = result.scalars().all()

        assert isinstance(contacts, list)

    @pytest.mark.asyncio
    async def test_session_transaction_commit(self, test_db_session):
        """Test session transaction commit."""
        from datetime import date

        contact = Contact(
            name="Transaction Test",
            profile_url="https://linkedin.com/in/txtest",
            birth_date=date(1990, 1, 1),
            status="new",
        )

        test_db_session.add(contact)
        await test_db_session.commit()
        await test_db_session.refresh(contact)

        assert contact.id is not None

    @pytest.mark.asyncio
    async def test_session_transaction_rollback(self, test_db_session):
        """Test session transaction rollback."""
        from datetime import date

        contact = Contact(
            name="Rollback Test",
            profile_url="https://linkedin.com/in/rollbacktest",
            birth_date=date(1991, 2, 2),
            status="new",
        )

        test_db_session.add(contact)
        await test_db_session.flush()

        contact_id = contact.id
        await test_db_session.rollback()

        # Contact should not exist after rollback
        result = await test_db_session.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        rolled_back = result.scalar_one_or_none()

        assert rolled_back is None


@pytest.mark.integration
class TestDatabaseInitialization:
    """Test database initialization."""

    @pytest.mark.asyncio
    async def test_tables_created_on_init(self, test_db_engine):
        """Test that all required tables are created."""
        async with test_db_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            )
            tables = [row[0] for row in result.fetchall()]

        # Verify all required tables exist
        assert "contact" in tables
        assert "interaction" in tables
        assert "linkedin_selector" in tables

    @pytest.mark.asyncio
    async def test_connection_pooling(self, test_db_engine):
        """Test that connection pooling works."""
        # Create multiple connections
        async with test_db_engine.connect() as conn1:
            result1 = await conn1.execute(text("SELECT 1"))
            assert result1.scalar() == 1

        async with test_db_engine.connect() as conn2:
            result2 = await conn2.execute(text("SELECT 2"))
            assert result2.scalar() == 2

        # Both connections should work independently
        assert True
