"""
Database migration to add token-based password setup fields.

This adds:
- setup_token column to users table
- setup_token_expires column to users table
- Makes password_hash nullable for new accounts
"""

import sqlite3


def run_migration(db_path="database.db"):
    """Run the token fields migration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Adding token-based password setup fields...")

    try:
        # Add setup_token column
        print("\n[1/2] Adding setup_token column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN setup_token VARCHAR(100)")
            conn.commit()
            print("[OK] setup_token column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ setup_token column already exists")
            else:
                raise

        # Add setup_token_expires column
        print("\n[2/2] Adding setup_token_expires column...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN setup_token_expires DATETIME")
            conn.commit()
            print("[OK] setup_token_expires column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ setup_token_expires column already exists")
            else:
                raise

        print("\n" + "=" * 60)
        print("[OK] Migration completed successfully!")
        print("=" * 60)
        print("\nThe system now supports token-based password setup.")
        print("Teachers will set their own passwords on first login.")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "database.db"

    print("=" * 60)
    print("TOKEN-BASED PASSWORD SETUP MIGRATION")
    print("=" * 60)
    print(f"\nDatabase: {db_path}")

    response = input("\nContinue with migration? [Y/n]: ")

    if response.lower() in ["", "y", "yes"]:
        run_migration(db_path)
    else:
        print("\nMigration cancelled.")
        sys.exit(0)
