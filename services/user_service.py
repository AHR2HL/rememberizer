"""User management service functions."""

import re
import secrets
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Organization


def create_user(
    email, password, role, first_name, last_name, organization_id, created_by_id=None
):
    """
    Create a new user with hashed password.

    Args:
        email: User's email address
        password: Plain text password (will be hashed), or None for token-based setup
        role: User role ('admin', 'teacher', 'student')
        first_name: User's first name
        last_name: User's last name
        organization_id: ID of the organization
        created_by_id: ID of the user who created this user (optional for admin)

    Returns:
        User: The created User object

    Raises:
        ValueError: If email already exists or password is invalid
    """
    # Validate email format
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        raise ValueError("Email already exists")

    # Validate role
    if role not in ["admin", "teacher", "student"]:
        raise ValueError("Role must be 'admin', 'teacher', or 'student'")

    # Handle password or setup token
    password_hash = None
    setup_token = None
    setup_token_expires = None

    if password:
        # Validate password
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Hash password
        password_hash = generate_password_hash(password, method="scrypt")
    else:
        # Generate setup token for first-time login
        setup_token = secrets.token_urlsafe(32)
        setup_token_expires = datetime.utcnow() + timedelta(
            days=7
        )  # Token valid for 7 days

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        first_name=first_name,
        last_name=last_name,
        organization_id=organization_id,
        created_by=created_by_id,
        setup_token=setup_token,
        setup_token_expires=setup_token_expires,
    )

    db.session.add(user)
    db.session.commit()

    return user


def authenticate_user(email, password):
    """
    Authenticate a user by email and password.

    Args:
        email: User's email address
        password: Plain text password

    Returns:
        User: The authenticated User object, or None if authentication fails
    """
    user = User.query.filter_by(email=email, is_active=True).first()

    if not user:
        return None

    if not check_password_hash(user.password_hash, password):
        return None

    return user


def get_students_by_teacher(teacher_id):
    """
    Get all students in the same organization as a teacher.

    Args:
        teacher_id: ID of the teacher

    Returns:
        list: List of User objects (students)
    """
    teacher = User.query.get(teacher_id)
    if not teacher:
        return []

    # Get all students in the same organization
    students = (
        User.query.filter_by(
            organization_id=teacher.organization_id, role="student", is_active=True
        )
        .order_by(User.last_name, User.first_name)
        .all()
    )

    return students
