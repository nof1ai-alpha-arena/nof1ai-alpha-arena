"""
Migration script to convert JSONL diary to SQLite database.

Run this once to migrate existing diary.jsonl data to the new database.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.db_manager import get_db_manager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def main():
    """Main migration function."""
    print("=" * 60)
    print("AI Trading Bot - Database Migration Script")
    print("=" * 60)
    print()

    # Initialize database manager
    logger.info("Initializing database...")
    db = get_db_manager()

    # Show current database stats
    print("\n[STATS] Current Database Stats (Before Migration):")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # Migrate JSONL diary
    print("\n[MIGRATE] Migrating diary.jsonl to database...")
    jsonl_path = 'data/diary.jsonl'

    if not os.path.exists(jsonl_path):
        print(f"[ERROR] Error: {jsonl_path} not found")
        print("   Nothing to migrate. Database is ready for use.")
        return

    try:
        count = db.migrate_jsonl_diary(jsonl_path)
        print(f"[OK] Successfully migrated {count} diary entries")

        # Backup original JSONL file
        backup_path = f"{jsonl_path}.backup"
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(jsonl_path, backup_path)
            print(f"[OK] Created backup: {backup_path}")

    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        logger.exception("Migration failed")
        return

    # Show final database stats
    print("\n[STATS] Final Database Stats (After Migration):")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    print("\n" + "=" * 60)
    print("[OK] Migration Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Bot will now use SQLite database instead of JSONL")
    print("2. Original diary.jsonl has been backed up to diary.jsonl.backup")
    print("3. You can safely delete diary.jsonl after verifying migration")
    print()


if __name__ == '__main__':
    main()
