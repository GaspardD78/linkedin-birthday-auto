"""
Database Migration System for APP_V2
Handles creation and verification of database indexes and schema changes.

This module provides utilities for managing database schema migrations
including index creation, verification, and performance baseline testing.
"""

import logging
from datetime import datetime
from sqlalchemy import text, MetaData, inspect
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """
    Handles database migrations and index management.
    Provides safe, atomic operations for schema changes.
    """

    # Define all critical indexes
    CRITICAL_INDEXES = {
        "contacts": [
            {"name": "idx_contact_birth_date", "columns": ["birth_date"]},
            {"name": "idx_contact_status", "columns": ["status"]},
            {"name": "idx_contact_created_at", "columns": ["created_at"]},
        ],
        "interactions": [
            {"name": "idx_interaction_contact_type", "columns": ["contact_id", "type"]},
        ],
        "linkedin_selectors": [
            {"name": "idx_selector_success", "columns": ["last_success_at"]},
        ],
    }

    @staticmethod
    async def verify_indexes(engine: AsyncEngine) -> Dict[str, Dict[str, bool]]:
        """
        Verify that all critical indexes exist.

        Returns:
            Dict mapping table names to index verification results
        """
        results = {}

        async with engine.connect() as conn:
            inspector = inspect(conn.sync_engine)

            for table_name, indexes in DatabaseMigration.CRITICAL_INDEXES.items():
                results[table_name] = {}

                # Get all indexes for this table
                table_indexes = inspector.get_indexes(table_name)
                index_names = {idx["name"] for idx in table_indexes}

                for index_def in indexes:
                    index_name = index_def["name"]
                    exists = index_name in index_names
                    results[table_name][index_name] = exists

                    status = "✅ PRESENT" if exists else "❌ MISSING"
                    logger.info(
                        f"{status} | Index: {index_name} "
                        f"(table: {table_name}, columns: {index_def['columns']})"
                    )

        return results

    @staticmethod
    async def create_missing_indexes(engine: AsyncEngine) -> Dict[str, List[str]]:
        """
        Create missing indexes.

        Returns:
            Dict mapping table names to list of created index names
        """
        created = {}

        async with engine.begin() as conn:
            # Get list of existing indexes
            inspector = inspect(conn.sync_engine)

            for table_name, indexes in DatabaseMigration.CRITICAL_INDEXES.items():
                created[table_name] = []
                table_indexes = inspector.get_indexes(table_name)
                existing_names = {idx["name"] for idx in table_indexes}

                for index_def in indexes:
                    index_name = index_def["name"]
                    columns = index_def["columns"]

                    if index_name not in existing_names:
                        # Build CREATE INDEX statement
                        columns_str = ", ".join(columns)
                        create_sql = (
                            f"CREATE INDEX IF NOT EXISTS {index_name} "
                            f"ON {table_name}({columns_str})"
                        )

                        try:
                            await conn.execute(text(create_sql))
                            created[table_name].append(index_name)
                            logger.info(f"✅ CREATED | Index: {index_name} (table: {table_name})")
                        except Exception as e:
                            logger.error(
                                f"❌ ERROR | Failed to create index {index_name}: {e}"
                            )
                    else:
                        logger.info(f"⏭️ SKIPPED | Index already exists: {index_name}")

        return created

    @staticmethod
    async def get_index_stats(engine: AsyncEngine) -> Dict[str, Dict]:
        """
        Get statistics about indexes (SQLite specific).

        Returns:
            Dict with index statistics including row counts
        """
        stats = {}

        async with engine.connect() as conn:
            # Get approximate table sizes
            for table_name in DatabaseMigration.CRITICAL_INDEXES.keys():
                try:
                    result = await conn.execute(
                        text(f"SELECT COUNT(*) as row_count FROM {table_name}")
                    )
                    count = result.scalar() or 0
                    stats[table_name] = {
                        "row_count": count,
                        "indexes": len(DatabaseMigration.CRITICAL_INDEXES[table_name]),
                    }
                except Exception as e:
                    logger.warning(f"Could not get stats for {table_name}: {e}")
                    stats[table_name] = {"row_count": 0, "indexes": 0}

        return stats

    @staticmethod
    async def generate_performance_report(
        engine: AsyncEngine,
        before_stats: Dict = None
    ) -> str:
        """
        Generate a performance report for index creation.

        Returns:
            Formatted report string
        """
        after_stats = await DatabaseMigration.get_index_stats(engine)

        report = [
            "\n" + "=" * 70,
            "DATABASE MIGRATION REPORT - INDEX CREATION",
            "=" * 70,
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "INDEX VERIFICATION:",
            "-" * 70,
        ]

        # Get verification results
        verification = await DatabaseMigration.verify_indexes(engine)

        total_required = 0
        total_present = 0

        for table_name, indexes in verification.items():
            table_stats = after_stats.get(table_name, {})
            rows = table_stats.get("row_count", 0)

            report.append(f"\n{table_name} (rows: {rows:,})")

            for index_name, exists in indexes.items():
                status = "✅" if exists else "❌"
                report.append(f"  {status} {index_name}")

                total_required += 1
                if exists:
                    total_present += 1

        report.append("\n" + "-" * 70)
        report.append(f"SUMMARY: {total_present}/{total_required} indexes present")
        report.append(f"Status: {'✅ READY FOR PRODUCTION' if total_present == total_required else '⚠️  INCOMPLETE'}")
        report.append("=" * 70 + "\n")

        return "\n".join(report)


async def run_migrations(engine: AsyncEngine) -> None:
    """
    Main migration runner - called during app initialization.

    Args:
        engine: SQLAlchemy async engine instance
    """
    logger.info("🔍 Starting database migration checks...")

    # Check current state
    verification = await DatabaseMigration.verify_indexes(engine)

    # Check if any indexes are missing
    missing_count = sum(
        1 for table_indexes in verification.values()
        for exists in table_indexes.values()
        if not exists
    )

    if missing_count > 0:
        logger.warning(f"⚠️  Found {missing_count} missing indexes, creating...")
        await DatabaseMigration.create_missing_indexes(engine)
    else:
        logger.info("✅ All indexes are present")

    # Generate and log report
    report = await DatabaseMigration.generate_performance_report(engine)
    logger.info(report)
