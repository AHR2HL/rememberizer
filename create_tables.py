"""Create database tables with current schema."""

from app import app
from models import db, Organization, User, create_user

if __name__ == "__main__":
    with app.app_context():
        print("Creating all tables...")
        db.create_all()
        print("Tables created successfully!")

        # Create default organization
        print("\nCreating default organization...")
        org = Organization.query.get(1)
        if not org:
            org = Organization(id=1, name="Default Organization")
            db.session.add(org)
            db.session.commit()
            print("Default organization created!")
        else:
            print("Default organization already exists")

        # Create admin account
        print("\nCreating admin account...")
        admin = User.query.filter_by(email="admin@admin.admin").first()
        if not admin:
            admin = create_user(
                email="admin@admin.admin",
                password="admin123",
                role="admin",
                first_name="Admin",
                last_name="User",
                organization_id=1,
            )
            print("Admin account created! Email: admin@admin.admin, Password: admin123")
        else:
            print("Admin account already exists")

        print("\nDatabase setup complete!")
