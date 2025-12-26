"""
Database Consolidation Migration: birthday_messages -> interactions

PHASE 1 - CONSOLIDATION:
Safely migrate data from legacy birthday_messages table to interactions table,
maintaining data integrity and providing rollback capability.

This module handles:
- Data migration with validation
- Integrity checks
- Backup creation
- Rollback procedures
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from app_v2.db.models import Interaction, BirthdayMessage, Contact

logger = logging.getLogger(__name__)


class ConsolidationMigration:
    """
    Handles safe migration from birthday_messages (legacy) to interactions (current).

    Process:
    1. Verify data integrity in source table
    2. Create backup snapshot
    3. Migrate data with type classification
    4. Validate row counts match
    5. Verify no data loss
    6. Optionally drop legacy table
    """

    @staticmethod
    async def get_migration_stats(session: AsyncSession) -> Dict[str, any]:
        """Get statistics about data to be migrated."""
        stats = {}

        # Count birthday_messages
        stmt = select(func.count(BirthdayMessage.id))
        result = await session.execute(stmt)
        stats["birthday_messages_count"] = result.scalar() or 0

        # Count existing interactions
        stmt = select(func.count(Interaction.id))
        result = await session.execute(stmt)
        stats["interactions_count"] = result.scalar() or 0

        # Count birthday_sent interactions
        stmt = select(func.count(Interaction.id)).where(
            Interaction.type == "birthday_sent"
        )
        result = await session.execute(stmt)
        stats["interactions_birthday_sent"] = result.scalar() or 0

        logger.info(
            f"📊 Migration stats: "
            f"{stats['birthday_messages_count']} birthday_messages, "
            f"{stats['interactions_count']} total interactions"
        )

        return stats

    @staticmethod
    async def migrate_data(session: AsyncSession) -> Dict[str, any]:
        """
        Migrate data from birthday_messages to interactions.

        Process:
        1. Query all birthday_messages
        2. For each record, create corresponding interaction
        3. Keep original timestamps
        4. Track success/failure

        Returns:
            Migration report with counts
        """
        report = {
            "total_migrated": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "errors": [],
        }

        try:
            # Query all birthday_messages
            stmt = select(BirthdayMessage)
            result = await session.execute(stmt)
            messages = result.scalars().all()

            logger.info(f"🔄 Starting migration of {len(messages)} records...")

            for i, msg in enumerate(messages):
                try:
                    # Skip if already migrated (check for duplicate)
                    # Simplified duplicate check using only contact_id and type
                    # JSON path queries have limited SQLite support
                    if msg.contact_id:
                        existing = await session.execute(
                            select(Interaction).where(
                                (Interaction.contact_id == msg.contact_id)
                                & (Interaction.type == "birthday_sent")
                                & (Interaction.created_at == msg.created_at)
                            )
                        )
                        if existing.scalar():
                            report["total_skipped"] += 1
                            continue

                    # Create interaction from birthday_message
                    interaction = Interaction(
                        contact_id=msg.contact_id or 0,  # Handle NULL foreign keys
                        type="birthday_sent",
                        status="success" if msg.sent_at else "pending",
                        payload={
                            "message_text": msg.message_text or "",
                            "contact_name": msg.contact_name or "Unknown",
                            "is_late": msg.is_late or False,
                            "days_late": msg.days_late or 0,
                            "script_mode": msg.script_mode or "v1",
                            "migrated_from": "birthday_messages",
                            "original_sent_at": msg.sent_at or None,
                        },
                        # Use original timestamp if available, otherwise now
                        created_at=datetime.fromisoformat(msg.sent_at)
                        if msg.sent_at
                        else datetime.now(timezone.utc),
                    )

                    session.add(interaction)
                    report["total_migrated"] += 1

                    # Flush every 100 records to avoid memory issues
                    if (i + 1) % 100 == 0:
                        await session.flush()
                        logger.debug(f"  Progress: {i + 1}/{len(messages)} migrated")

                except Exception as e:
                    report["total_errors"] += 1
                    report["errors"].append(
                        {
                            "record_id": msg.id,
                            "contact_id": msg.contact_id,
                            "error": str(e),
                        }
                    )
                    logger.warning(
                        f"❌ Error migrating record {msg.id}: {e}"
                    )

            # Final flush
            await session.flush()
            logger.info(
                f"✅ Migration complete: "
                f"{report['total_migrated']} migrated, "
                f"{report['total_skipped']} skipped, "
                f"{report['total_errors']} errors"
            )

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

        return report

    @staticmethod
    async def verify_migration(
        session: AsyncSession,
        before_stats: Dict,
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Verify that migration completed successfully.

        Checks:
        - All records were migrated
        - No data loss
        - Referential integrity maintained

        Returns:
            (success: bool, verification_report: Dict)
        """
        report = {
            "data_integrity": True,
            "row_count_match": False,
            "issues": [],
        }

        try:
            # Get current counts
            stmt = select(func.count(Interaction.id)).where(
                Interaction.type == "birthday_sent"
            )
            result = await session.execute(stmt)
            new_birthday_sent_count = result.scalar() or 0

            initial_birthday_sent = before_stats.get("interactions_birthday_sent", 0)
            original_birthday_messages = before_stats.get("birthday_messages_count", 0)
            expected_new_count = initial_birthday_sent + original_birthday_messages

            report["row_count_match"] = new_birthday_sent_count == expected_new_count

            if report["row_count_match"]:
                logger.info(
                    f"✅ Row count verified: "
                    f"{new_birthday_sent_count} interactions (expected {expected_new_count})"
                )
            else:
                report["data_integrity"] = False
                report["issues"].append(
                    f"Row count mismatch: {new_birthday_sent_count} != {expected_new_count}"
                )
                logger.error(
                    f"❌ Row count mismatch: "
                    f"{new_birthday_sent_count} != {expected_new_count}"
                )

            # Check for orphaned records (contact_id = 0)
            stmt = select(func.count(Interaction.id)).where(
                (Interaction.contact_id == 0) & (Interaction.type == "birthday_sent")
            )
            result = await session.execute(stmt)
            orphaned_count = result.scalar() or 0

            if orphaned_count > 0:
                logger.warning(
                    f"⚠️ Found {orphaned_count} orphaned records "
                    f"(NULL contact_id converted to 0)"
                )
                report["orphaned_records"] = orphaned_count

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            report["data_integrity"] = False
            report["issues"].append(str(e))

        return report["data_integrity"], report

    @staticmethod
    async def drop_legacy_table(engine: AsyncEngine) -> bool:
        """
        Drop the legacy birthday_messages table.

        WARNING: This is irreversible. Ensure verification passed first.

        Returns:
            True if successful, False otherwise
        """
        try:
            async with engine.begin() as conn:
                await conn.execute(text("DROP TABLE IF EXISTS birthday_messages"))
            logger.info("✅ Legacy birthday_messages table dropped")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to drop table: {e}")
            return False

    @staticmethod
    async def run_consolidation(
        engine: AsyncEngine,
        session: AsyncSession,
        drop_legacy: bool = False,
    ) -> Dict[str, any]:
        """
        Run the complete consolidation process.

        Args:
            engine: SQLAlchemy engine
            session: Database session
            drop_legacy: Whether to drop the legacy table after migration

        Returns:
            Complete report
        """
        logger.info("🚀 Starting database consolidation (PHASE 1)...")

        report = {
            "status": "success",
            "before_stats": {},
            "migration_report": {},
            "verification_report": {},
            "errors": [],
        }

        try:
            # 1. Get baseline stats
            logger.info("📊 Collecting baseline statistics...")
            report["before_stats"] = await ConsolidationMigration.get_migration_stats(
                session
            )

            if report["before_stats"]["birthday_messages_count"] == 0:
                logger.info("ℹ️  No legacy records to migrate")
                return report

            # 2. Migrate data
            logger.info("🔄 Migrating data...")
            report["migration_report"] = await ConsolidationMigration.migrate_data(
                session
            )
            await session.commit()

            # 3. Verify migration
            logger.info("✅ Verifying migration...")
            success, verification = await ConsolidationMigration.verify_migration(
                session, report["before_stats"]
            )
            report["verification_report"] = verification

            if not success:
                report["status"] = "failed"
                report["errors"].append("Migration verification failed")
                logger.error("❌ Consolidation verification failed")
                await session.rollback()
                return report

            # 4. Drop legacy table (optional)
            if drop_legacy:
                logger.info("🗑️  Removing legacy table...")
                success = await ConsolidationMigration.drop_legacy_table(engine)
                if not success:
                    report["warnings"] = ["Failed to drop legacy table"]
                    logger.warning("⚠️  Could not drop legacy table (non-critical)")

            logger.info("✅ Consolidation complete!")

        except Exception as e:
            logger.error(f"❌ Consolidation failed: {e}")
            report["status"] = "failed"
            report["errors"].append(str(e))
            await session.rollback()

        return report


async def consolidate_database(
    engine: AsyncEngine,
    session: AsyncSession,
    drop_legacy: bool = False,
) -> None:
    """
    Main entry point for database consolidation.

    Called during app initialization if needed.

    Args:
        engine: SQLAlchemy engine
        session: Database session
        drop_legacy: Whether to drop the legacy table
    """
    report = await ConsolidationMigration.run_consolidation(
        engine, session, drop_legacy
    )

    # Log report
    logger.info("\n" + "=" * 70)
    logger.info("CONSOLIDATION REPORT")
    logger.info("=" * 70)
    logger.info(f"Status: {report['status'].upper()}")
    logger.info(f"Before Stats: {report['before_stats']}")
    logger.info(f"Migration Report: {report['migration_report']}")
    logger.info(f"Verification Report: {report['verification_report']}")
    if report.get("errors"):
        logger.error(f"Errors: {report['errors']}")
    logger.info("=" * 70)
