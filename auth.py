"""
Authentication module for Rememberizer multi-user system.

Provides Flask-Login integration, password hashing, and role-based access control.
"""

from functools import wraps
from datetime import datetime
from flask import redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


class AuthUser(UserMixin):
    """
    User wrapper class for Flask-Login.

    Flask-Login requires a User class with specific methods (get_id, is_authenticated, etc.).
    This wrapper provides those methods while using our database User model.
    """

    def __init__(self, user):
        """
        Initialize AuthUser with a database User object.

        Args:
            user: A User model instance from the database
        """
        self.user = user

    def get_id(self):
        """Return user ID as string (required by Flask-Login)."""
        return str(self.user.id)

    @property
    def is_active(self):
        """Return True if user is active."""
        return self.user.is_active

    @property
    def is_authenticated(self):
        """Return True if user is authenticated (always True for valid users)."""
        return True

    @property
    def is_anonymous(self):
        """Return False (authenticated users are not anonymous)."""
        return False

    @property
    def id(self):
        """Return user ID."""
        return self.user.id

    @property
    def email(self):
        """Return user email."""
        return self.user.email

    @property
    def role(self):
        """Return user role."""
        return self.user.role

    @property
    def first_name(self):
        """Return user's first name."""
        return self.user.first_name

    @property
    def last_name(self):
        """Return user's last name."""
        return self.user.last_name

    @property
    def organization_id(self):
        """Return user's organization ID."""
        return self.user.organization_id

    def get_full_name(self):
        """Return user's full name."""
        return self.user.get_full_name()


@login_manager.user_loader
def load_user(user_id):
    """
    Load user by ID for Flask-Login.

    This callback is used by Flask-Login to reload the user object from the user ID
    stored in the session.

    Args:
        user_id: The user ID as a string

    Returns:
        AuthUser: Wrapped user object, or None if user not found
    """
    from models import User

    user = User.query.get(int(user_id))
    if user:
        return AuthUser(user)
    return None


def hash_password(password):
    """
    Hash a plain text password using scrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash, password):
    """
    Verify a password against its hash.

    Args:
        password_hash: The hashed password
        password: Plain text password to verify

    Returns:
        bool: True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


def role_required(*roles):
    """
    Decorator to restrict access to specific user roles.

    Usage:
        @role_required('admin')
        def admin_only_view():
            ...

        @role_required('teacher', 'admin')
        def teacher_or_admin_view():
            ...

    Args:
        *roles: One or more role names that are allowed access

    Returns:
        Function decorator
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))

            if current_user.role not in roles:
                abort(403)  # Forbidden

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def get_current_user():
    """
    Get the current logged-in user.

    Returns:
        AuthUser: Current user, or None if not logged in
    """
    if current_user.is_authenticated:
        return current_user
    return None


def update_last_active(user_id):
    """
    Update the last_active timestamp for a user.

    Args:
        user_id: ID of the user to update
    """
    from models import User, db

    user = User.query.get(user_id)
    if user:
        user.last_active = datetime.utcnow()
        db.session.commit()


def is_authenticated():
    """
    Check if current user is authenticated.

    Returns:
        bool: True if user is logged in, False otherwise
    """
    return current_user.is_authenticated


def has_role(*roles):
    """
    Check if current user has one of the specified roles.

    Args:
        *roles: One or more role names to check

    Returns:
        bool: True if user has one of the roles, False otherwise
    """
    if not current_user.is_authenticated:
        return False

    return current_user.role in roles
