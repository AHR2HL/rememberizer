"""Migration script to add fact_states table to existing database."""

from app import app, db

if __name__ == "__main__":
    with app.app_context():
        # Create all tables (will only create missing ones)
        db.create_all()
        print("Migration complete: fact_states table created")
