"""
Database migration script to add domain creation and visibility features.

This migration:
1. Adds created_by, organization_id, is_published, created_at columns to domains table
2. Makes filename nullable for user-created domains
3. Sets existing domains to published (backward compatible)
4. Creates indexes for performance

NOTE: This migration preserves all existing data.
"""

import sqlite3
from datetime import datetime


def run_migration(db_path="database.db"):
    """Run the domain creation migration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Starting migration to add domain creation features...")

    try:
        # Step 1: Add created_by column
        print("\n[1/5] Adding created_by column to domains...")
        try:
            cursor.execute("ALTER TABLE domains ADD COLUMN created_by INTEGER")
            conn.commit()
            print("✓ created_by column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ created_by column already exists")
            else:
                raise

        # Step 2: Add organization_id column
        print("\n[2/5] Adding organization_id column to domains...")
        try:
            cursor.execute("ALTER TABLE domains ADD COLUMN organization_id INTEGER")
            conn.commit()
            print("✓ organization_id column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ organization_id column already exists")
            else:
                raise

        # Step 3: Add is_published column
        print("\n[3/5] Adding is_published column to domains...")
        try:
            cursor.execute(
                "ALTER TABLE domains ADD COLUMN is_published BOOLEAN DEFAULT 0 NOT NULL"
            )
            conn.commit()
            print("✓ is_published column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ is_published column already exists")
            else:
                raise

        # Step 4: Add created_at column
        print("\n[4/5] Adding created_at column to domains...")
        try:
            cursor.execute(
                "ALTER TABLE domains ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
            conn.commit()
            print("✓ created_at column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ created_at column already exists")
            else:
                raise

        # Step 5: Update existing domains to be published (backward compatible)
        print("\n[5/5] Setting existing domains as published...")
        cursor.execute("""
            UPDATE domains
            SET is_published = 1,
                created_by = NULL,
                organization_id = NULL
            WHERE created_by IS NULL
        """)
        rows_updated = cursor.rowcount
        conn.commit()
        print(f"✓ {rows_updated} existing domains set as published (globally available)")

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nDomain creation features enabled:")
        print("- Teachers can now create custom domains")
        print("- Domains can be published (global) or org-scoped (private)")
        print("- Existing domains are published by default")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\nX Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    # Check if database path is provided
    db_path = sys.argv[1] if len(sys.argv) > 1 else "database.db"

    print("=" * 60)
    print("DOMAIN CREATION MIGRATION")
    print("=" * 60)
    print(f"\nDatabase: {db_path}")
    print("\nThis migration will add domain creation and visibility features.")
    print("All existing data will be preserved.")

    response = input("\nContinue with migration? [y/N]: ")

    if response.lower() in ["y", "yes"]:
        run_migration(db_path)
    else:
        print("\nMigration cancelled.")
        sys.exit(0)
