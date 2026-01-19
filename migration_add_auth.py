"""
Database migration script to add multi-user authentication system.

This migration:
1. Creates new tables (organizations, users, user_domain_assignments)
2. Adds user_id columns to FactState and Attempt
3. Creates default organization
4. DELETES all existing FactState and Attempt records (clean slate)
5. Makes user_id columns non-nullable
6. Creates indexes for performance

WARNING: This migration will delete all existing progress data.
"""

import sqlite3
from datetime import datetime


def run_migration(db_path="database.db"):
    """Run the authentication system migration."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Starting migration to add authentication system...")

    try:
        # Step 1: Create Organizations table
        print("\n[1/8] Creating organizations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL UNIQUE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✓ Organizations table created")

        # Step 2: Create Users table
        print("\n[2/8] Creating users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                organization_id INTEGER NOT NULL,
                created_by INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        conn.commit()
        print("✓ Users table created")

        # Step 3: Create UserDomainAssignments table
        print("\n[3/8] Creating user_domain_assignments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_domain_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                domain_id INTEGER NOT NULL,
                assigned_by INTEGER NOT NULL,
                assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (domain_id) REFERENCES domains(id),
                FOREIGN KEY (assigned_by) REFERENCES users(id),
                UNIQUE (user_id, domain_id)
            )
        """)
        conn.commit()
        print("✓ User domain assignments table created")

        # Step 4: Create default organization
        print("\n[4/8] Creating default organization...")
        cursor.execute(
            """
            INSERT OR IGNORE INTO organizations (id, name, created_at)
            VALUES (1, 'Default Organization', ?)
        """,
            (datetime.utcnow().isoformat(),),
        )
        conn.commit()
        print("✓ Default organization created (id=1)")

        # Step 5: Add user_id column to fact_states (nullable initially)
        print("\n[5/8] Adding user_id column to fact_states...")
        try:
            cursor.execute("ALTER TABLE fact_states ADD COLUMN user_id INTEGER")
            conn.commit()
            print("✓ user_id column added to fact_states")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ user_id column already exists in fact_states")
            else:
                raise

        # Step 6: Add user_id and session_id columns to attempts
        print("\n[6/8] Adding user_id and session_id columns to attempts...")
        try:
            cursor.execute("ALTER TABLE attempts ADD COLUMN user_id INTEGER")
            print("✓ user_id column added to attempts")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ user_id column already exists in attempts")
            else:
                raise

        try:
            cursor.execute("ALTER TABLE attempts ADD COLUMN session_id VARCHAR(50)")
            print("✓ session_id column added to attempts")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ session_id column already exists in attempts")
            else:
                raise

        conn.commit()

        # Step 7: DELETE all existing progress data (clean slate)
        print("\n[7/8] Deleting all existing progress data...")
        cursor.execute("SELECT COUNT(*) FROM fact_states")
        fact_state_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attempts")
        attempt_count = cursor.fetchone()[0]

        print(f"  - Found {fact_state_count} fact states")
        print(f"  - Found {attempt_count} attempts")

        cursor.execute("DELETE FROM fact_states")
        cursor.execute("DELETE FROM attempts")
        conn.commit()
        print("✓ All progress data deleted (clean slate for multi-user)")

        # Step 8: Create indexes for performance
        print("\n[8/8] Creating indexes...")

        # Index on users.email for login lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email)
        """)

        # Index on users.organization_id for org-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_organization
            ON users(organization_id)
        """)

        # Index on fact_states.user_id for user progress queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fact_states_user
            ON fact_states(user_id)
        """)

        # Index on attempts.user_id for user attempt queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_user
            ON attempts(user_id)
        """)

        # Index on user_domain_assignments.user_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assignments_user
            ON user_domain_assignments(user_id)
        """)

        # Index on user_domain_assignments.domain_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_assignments_domain
            ON user_domain_assignments(domain_id)
        """)

        conn.commit()
        print("✓ All indexes created")

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run the application: python app.py")
        print("2. You will be prompted to create an admin account")
        print("3. Use admin@admin.admin to log in with your chosen password")
        print("\nNOTE: All previous progress data has been deleted.")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    # Check if database path is provided
    db_path = sys.argv[1] if len(sys.argv) > 1 else "database.db"

    print("=" * 60)
    print("AUTHENTICATION SYSTEM MIGRATION")
    print("=" * 60)
    print(f"\nDatabase: {db_path}")
    print("\n⚠ WARNING: This will delete all existing progress data!")
    print("          (FactState and Attempt records will be cleared)")

    response = input("\nContinue with migration? [y/N]: ")

    if response.lower() in ["y", "yes"]:
        run_migration(db_path)
    else:
        print("\nMigration cancelled.")
        sys.exit(0)
