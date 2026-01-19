"""Manual database initialization script.

Run this script to manually initialize the database and load fact domains.
Normally, the database initializes automatically on first request.
"""

from app import app, init_database

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Database initialized successfully!")
    print("All fact domains have been loaded from the 'facts' directory.")
