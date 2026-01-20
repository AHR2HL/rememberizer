"""Main Flask application for Rememberizer quiz app."""

import os
from flask import Flask
from models import db, Domain, Fact, User, Organization
from facts_loader import load_all_domains_from_directory
from auth import login_manager

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Initialize Flask-Login
login_manager.init_app(app)

# Flag to track if database has been initialized
_db_initialized = False


@app.template_filter("center_in_box")
def center_in_box(text, width=35):
    """
    Center text within a fixed width for terminal box display.

    Args:
        text: The text to center
        width: The interior width of the box (default: 35)

    Returns:
        String with text centered using spaces, exactly 'width' characters long
    """
    if not text:
        text = ""

    # Convert to string and strip existing whitespace
    text = str(text).strip()

    # Use Python's built-in center method which handles padding automatically
    return text.center(width)


@app.template_filter("progress_string")
def progress_string_filter(domain_id):
    """Generate progress string for a domain for the current user."""
    from services.progress_service import get_progress_string
    from flask_login import current_user

    # If user is not authenticated, return empty string
    if not current_user.is_authenticated:
        return ""

    return get_progress_string(domain_id, current_user.id)


@app.template_filter("format_field_name")
def format_field_name_filter(field_name):
    """Format field name for display by replacing underscores with spaces."""
    return field_name.replace("_", " ")


@app.template_filter("singularize")
def singularize_filter(domain_name):
    """Singularize domain name for display."""
    from quiz_logic import singularize_domain_name

    return singularize_domain_name(domain_name)


def init_database():
    """Initialize database and load fact domains."""
    global _db_initialized
    if _db_initialized:
        return

    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()

        # Load all JSON files from facts directory
        load_all_domains_from_directory("facts")

        # Check if admin account exists
        from services.user_service import create_user

        admin = User.query.filter_by(role="admin").first()

        if not admin:
            # Ensure default organization exists
            org = Organization.query.get(1)
            if not org:
                org = Organization(id=1, name="Default Organization")
                db.session.add(org)
                db.session.commit()

            # Skip interactive prompts during testing
            if not app.config.get("TESTING"):
                print("\n" + "=" * 60)
                print("FIRST-TIME SETUP: ADMIN ACCOUNT CREATION")
                print("=" * 60)
                print("\nNo admin account found. You need to create one to manage")
                print("teachers and students in the Rememberizer system.")
                print("\nThe admin email will be: admin@admin.admin")

                response = input("\nCreate admin account now? [Y/n]: ").strip().lower()

                if response in ["", "y", "yes"]:
                    while True:
                        password = input("Enter admin password (min 8 chars): ").strip()

                        if len(password) < 8:
                            print(
                                "[ERROR] Password must be at least 8 characters "
                                "long. Try again."
                            )
                            continue

                        # Confirm password
                        confirm = input("Confirm admin password: ").strip()

                        if password != confirm:
                            print("[ERROR] Passwords do not match. Try again.\n")
                            continue

                        # Create admin user
                        try:
                            admin = create_user(
                                email="admin@admin.admin",
                                password=password,
                                role="admin",
                                first_name="Admin",
                                last_name="User",
                                organization_id=1,
                            )

                            print("\n" + "=" * 60)
                            print("[OK] Admin account created successfully!")
                            print("=" * 60)
                            print("\nLogin credentials:")
                            print("  Email:    admin@admin.admin")
                            print("  Password: (the password you just set)")
                            print("\nYou can now start the application and log in.")
                            print("=" * 60 + "\n")
                            break

                        except ValueError as e:
                            print(f"[ERROR] Error creating admin: {e}")
                            break
                else:
                    print("\nAdmin account creation skipped.")
                    print("You can create one later by running the application again.")
                    print("=" * 60 + "\n")

        _db_initialized = True


@app.before_request
def ensure_database():
    """Ensure database is initialized before first request."""
    init_database()


@app.before_request
def update_last_active():
    """Update last_active timestamp for authenticated users."""
    from flask_login import current_user
    from datetime import datetime

    if current_user.is_authenticated:
        # Update last_active timestamp
        current_user.user.last_active = datetime.utcnow()
        db.session.commit()


# ============================================================================
# REGISTER BLUEPRINTS
# ============================================================================

from blueprints.auth_routes import auth_bp
from blueprints.admin import admin_bp
from blueprints.teacher import teacher_bp
from blueprints.student import student_bp
from blueprints.quiz import quiz_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(student_bp)
app.register_blueprint(quiz_bp)


if __name__ == "__main__":
    init_database()
    app.run(debug=True, host="0.0.0.0", port=5000)
