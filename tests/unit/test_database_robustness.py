
import os
import pytest
import logging
from src.core.database import Database, retry_on_lock

def test_database_init_and_operations():
    db_path = "test_robustness.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)

    # Test connection and WAL mode check
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        # Note: WAL mode might not be default enabled on all sqlite versions without explicit config,
        # but our class enables it.
        assert mode.upper() == "WAL"

    # Test Add Contact
    contact_id = db.add_contact("Test User", "http://linkedin.com/in/test", 50.0)
    assert contact_id > 0

    # Test Read
    contact = db.get_contact_by_name("Test User")
    assert contact is not None
    assert contact["linkedin_url"] == "http://linkedin.com/in/test"

    # Cleanup
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
        os.remove(f"{db_path}-shm") if os.path.exists(f"{db_path}-shm") else None
        os.remove(f"{db_path}-wal") if os.path.exists(f"{db_path}-wal") else None
