"""Setup database properly."""

import sys
import os

# Make sure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Domain, Organization, User, Fact, create_user
from facts_loader import load_all_domains_from_directory

if __name__ == "__main__":
    with app.app_context():
        print("Step 1: Dropping all tables...")
        db.drop_all()
        print("Done!")

        print("\nStep 2: Creating all tables...")
        db.create_all()
        print("Done!")

        print("\nStep 3: Verifying tables...")
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Tables created: {tables}")

        # Check domains table schema
        if 'domains' in tables:
            columns = inspector.get_columns('domains')
            print("\nDomains table columns:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']}")

        print("\nStep 4: Creating default organization...")
        org = Organization(id=1, name="Default Organization")
        db.session.add(org)
        db.session.commit()
        print("Done!")

        print("\nStep 5: Creating admin account...")
        admin = create_user(
            email="admin@admin.admin",
            password="admin123",
            role="admin",
            first_name="Admin",
            last_name="User",
            organization_id=1,
        )
        print(f"Admin created: {admin.email}")

        print("\nStep 6: Loading fact domains from JSON files...")
        load_all_domains_from_directory("facts")
        domain_count = Domain.query.count()
        print(f"Loaded {domain_count} domains")

        print("\n" + "=" * 60)
        print("Database setup complete!")
        print("=" * 60)
        print("Admin credentials:")
        print("  Email: admin@admin.admin")
        print("  Password: admin123")
        print("=" * 60)
