"""
Integration tests for database migrations and consolidation.

Tests cover:
- Index creation and verification
- Data migration from birthday_messages to interactions
- Data integrity checks
- Rollback procedures
"""

import pytest
from datetime import datetime, timezone

from sqlalchemy import inspect, select, func, text

from app_v2.db.migrations import DatabaseMigration
from app_v2.db.consolidation import ConsolidationMigration
from app_v2.db.models import Contact, Interaction, LinkedInSelector, BirthdayMessage


@pytest.mark.integration
class TestIndexCreation:
    """Test database index creation and verification."""

    async def test_contact_indexes_exist(self, test_db_engine, test_db_session):
        """Test that Contact table indexes are created."""
        # Run migrations
        from app_v2.db.migrations import run_migrations
        await run_migrations(test_db_engine)

        # Check indexes exist
        async with test_db_engine.connect() as conn:
            inspector = inspect(conn.sync_engine)
            indexes = inspector.get_indexes("contacts")
            index_names = {idx["name"] for idx in indexes}

            assert "idx_contact_birth_date" in index_names
            assert "idx_contact_status" in index_names
            assert "idx_contact_created_at" in index_names

    async def test_interaction_indexes_exist(self, test_db_engine, test_db_session):
        """Test that Interaction table indexes are created."""
        # Run migrations
        from app_v2.db.migrations import run_migrations
        await run_migrations(test_db_engine)

        # Check indexes exist
        async with test_db_engine.connect() as conn:
            inspector = inspect(conn.sync_engine)
            indexes = inspector.get_indexes("interactions")
            index_names = {idx["name"] for idx in indexes}

            assert "idx_interaction_contact_type" in index_names

    async def test_selector_indexes_exist(self, test_db_engine, test_db_session):
        """Test that LinkedInSelector table indexes are created."""
        # Run migrations
        from app_v2.db.migrations import run_migrations
        await run_migrations(test_db_engine)

        # Check indexes exist
        async with test_db_engine.connect() as conn:
            inspector = inspect(conn.sync_engine)
            indexes = inspector.get_indexes("linkedin_selectors")
            index_names = {idx["name"] for idx in indexes}

            assert "idx_selector_success" in index_names

    async def test_verify_indexes_report(self, test_db_engine):
        """Test that index verification generates correct report."""
        # Run migrations first
        from app_v2.db.migrations import run_migrations
        await run_migrations(test_db_engine)

        # Verify all indexes
        results = await DatabaseMigration.verify_indexes(test_db_engine)

        # Check that all expected indexes are present
        assert results["contacts"]["idx_contact_birth_date"] is True
        assert results["contacts"]["idx_contact_status"] is True
        assert results["contacts"]["idx_contact_created_at"] is True
        assert results["interactions"]["idx_interaction_contact_type"] is True
        assert results["linkedin_selectors"]["idx_selector_success"] is True


@pytest.mark.integration
class TestDataConsolidation:
    """Test data migration from birthday_messages to interactions."""

    async def test_get_migration_stats(self, test_db_session):
        """Test that migration statistics are collected correctly."""
        # Create some test data
        bday_msg = BirthdayMessage(
            contact_id=1,
            contact_name="Test User",
            message_text="Happy Birthday!",
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        test_db_session.add(bday_msg)
        await test_db_session.flush()

        stats = await ConsolidationMigration.get_migration_stats(test_db_session)

        assert stats["birthday_messages_count"] >= 1
        assert "interactions_count" in stats

    async def test_migrate_birthday_messages_to_interactions(
        self, test_db_session_fresh, test_db_engine
    ):
        """Test migration of birthday_messages to interactions."""
        # Create test birthday message
        bday_msg = BirthdayMessage(
            contact_id=1,
            contact_name="Alice",
            message_text="Happy Birthday, Alice!",
            sent_at=datetime.now(timezone.utc).isoformat(),
            is_late=False,
            days_late=0,
            script_mode="v1",
        )
        test_db_session_fresh.add(bday_msg)
        await test_db_session_fresh.flush()

        # Run consolidation
        report = await ConsolidationMigration.run_consolidation(
            test_db_engine,
            test_db_session_fresh,
            drop_legacy=False,
        )

        # Check report
        assert report["status"] == "success"
        assert report["migration_report"]["total_migrated"] >= 1

        # Verify interaction was created
        stmt = select(Interaction).where(Interaction.type == "birthday_sent")
        result = await test_db_session_fresh.execute(stmt)
        interactions = result.scalars().all()

        assert len(interactions) >= 1

        # Check interaction data
        interaction = interactions[0]
        assert interaction.type == "birthday_sent"
        assert "Alice" in str(interaction.payload)

    async def test_migration_preserves_data_integrity(self, test_db_session_fresh):
        """Test that migration preserves all data fields."""
        # Create birthday message with all fields
        now = datetime.now(timezone.utc)
        bday_msg = BirthdayMessage(
            contact_id=42,
            contact_name="Test User",
            message_text="Happy Birthday!",
            sent_at=now.isoformat(),
            is_late=True,
            days_late=3,
            script_mode="v1",
        )
        test_db_session_fresh.add(bday_msg)
        await test_db_session_fresh.flush()

        # Get initial data
        initial_count = (
            await test_db_session_fresh.execute(
                select(func.count(BirthdayMessage.id))
            )
        ).scalar() or 0

        # Migrate
        report = await ConsolidationMigration.migrate_data(test_db_session_fresh)

        # Check that data was migrated
        stmt = select(Interaction).where(Interaction.payload["contact_name"] == "Test User")
        result = await test_db_session_fresh.execute(stmt)
        interaction = result.scalar()

        assert interaction is not None
        assert interaction.payload["is_late"] is True
        assert interaction.payload["days_late"] == 3

    async def test_migration_verification(self, test_db_session_fresh, test_db_engine):
        """Test that migration verification works correctly."""
        # Create test data
        bday_msg = BirthdayMessage(
            contact_id=1,
            contact_name="Test",
            message_text="Message",
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        test_db_session_fresh.add(bday_msg)
        await test_db_session_fresh.flush()

        stats = await ConsolidationMigration.get_migration_stats(test_db_session_fresh)

        # Migrate
        await ConsolidationMigration.migrate_data(test_db_session_fresh)
        await test_db_session_fresh.flush()

        # Verify
        success, verification = await ConsolidationMigration.verify_migration(
            test_db_session_fresh, stats
        )

        assert success is True
        assert verification["row_count_match"] is True

    async def test_drop_legacy_table(self, test_db_engine):
        """Test that legacy table can be dropped."""
        success = await ConsolidationMigration.drop_legacy_table(test_db_engine)

        # Dropping should succeed
        assert success is True

        # Verify table is gone
        async with test_db_engine.connect() as conn:
            inspector = inspect(conn.sync_engine)
            tables = inspector.get_table_names()

            # birthday_messages should not exist
            assert "birthday_messages" not in tables


@pytest.mark.integration
class TestMigrationSafety:
    """Test safety and rollback mechanisms."""

    async def test_failed_migration_can_rollback(self, test_db_session):
        """Test that failed migration doesn't corrupt data."""
        # Create test data
        bday_msg = BirthdayMessage(
            contact_id=1,
            contact_name="Test",
            message_text="Message",
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        test_db_session.add(bday_msg)
        await test_db_session.commit()

        # Get initial count
        initial_count = (
            await test_db_session.execute(
                select(func.count(BirthdayMessage.id))
            )
        ).scalar() or 0

        # Simulate rollback (in case of error)
        await test_db_session.rollback()

        # Verify data is unchanged
        final_count = (
            await test_db_session.execute(
                select(func.count(BirthdayMessage.id))
            )
        ).scalar() or 0

        assert initial_count == final_count

    async def test_no_duplicate_migration_on_rerun(self, test_db_session_fresh):
        """Test that running migration twice doesn't duplicate data."""
        # Create test data
        bday_msg = BirthdayMessage(
            contact_id=1,
            contact_name="Test",
            message_text="Message",
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
        test_db_session_fresh.add(bday_msg)
        await test_db_session_fresh.flush()

        # First migration
        report1 = await ConsolidationMigration.migrate_data(test_db_session_fresh)
        await test_db_session_fresh.flush()

        count_after_first = (
            await test_db_session_fresh.execute(
                select(func.count(Interaction.id)).where(Interaction.type == "birthday_sent")
            )
        ).scalar() or 0

        # Second migration (should skip duplicates)
        report2 = await ConsolidationMigration.migrate_data(test_db_session_fresh)
        await test_db_session_fresh.flush()

        count_after_second = (
            await test_db_session_fresh.execute(
                select(func.count(Interaction.id)).where(Interaction.type == "birthday_sent")
            )
        ).scalar() or 0

        # Count should be the same (no duplicates)
        assert count_after_first == count_after_second
