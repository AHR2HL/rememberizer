"""Tests for authentication functionality."""

import pytest
from models import User
from services.user_service import authenticate_user, create_user
from werkzeug.security import check_password_hash


class TestUserCreation:
    """Test user creation functionality."""

    def test_create_admin_user(self, app):
        """Test creating an admin user."""
        with app.app_context():
            admin = create_user(
                email="newadmin@test.com",
                password="password123",
                role="admin",
                first_name="New",
                last_name="Admin",
                organization_id=1,
            )
            assert admin.email == "newadmin@test.com"
            assert admin.role == "admin"
            assert admin.password_hash is not None
            assert check_password_hash(admin.password_hash, "password123")

    def test_create_teacher_without_password(self, app):
        """Test creating a teacher with token-based setup."""
        with app.app_context():
            teacher = create_user(
                email="newteacher@test.com",
                password=None,
                role="teacher",
                first_name="New",
                last_name="Teacher",
                organization_id=1,
            )
            assert teacher.email == "newteacher@test.com"
            assert teacher.role == "teacher"
            assert teacher.password_hash is None
            assert teacher.setup_token is not None
            assert teacher.setup_token_expires is not None

    def test_create_duplicate_email_fails(self, app, admin_user):
        """Test that creating a user with duplicate email fails."""
        with app.app_context():
            with pytest.raises(ValueError, match="Email already exists"):
                create_user(
                    email="admin@test.com",
                    password="password123",
                    role="teacher",
                    first_name="Duplicate",
                    last_name="User",
                    organization_id=1,
                )

    def test_invalid_email_fails(self, app):
        """Test that invalid email format fails."""
        with app.app_context():
            with pytest.raises(ValueError, match="Invalid email format"):
                create_user(
                    email="notanemail",
                    password="password123",
                    role="student",
                    first_name="Invalid",
                    last_name="Email",
                    organization_id=1,
                )


class TestAuthentication:
    """Test user authentication."""

    def test_successful_login(self, app, admin_user):
        """Test successful user authentication."""
        with app.app_context():
            user = authenticate_user("admin@test.com", "adminpass123")
            assert user is not None
            assert user.email == "admin@test.com"

    def test_wrong_password(self, app, admin_user):
        """Test login with wrong password."""
        with app.app_context():
            user = authenticate_user("admin@test.com", "wrongpassword")
            assert user is None

    def test_nonexistent_user(self, app):
        """Test login with nonexistent email."""
        with app.app_context():
            user = authenticate_user("nonexistent@test.com", "password")
            assert user is None

    def test_inactive_user_cannot_login(self, app, student_user):
        """Test that deactivated users cannot log in."""
        with app.app_context():
            # Deactivate user
            student = User.query.get(student_user.id)
            student.is_active = False
            from models import db

            db.session.commit()

            # Try to authenticate
            user = authenticate_user("student@test.com", "studentpass123")
            assert user is None


class TestLoginRoutes:
    """Test login/logout routes."""

    def test_login_page_loads(self, client):
        """Test that login page loads successfully."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"LOGIN" in response.data

    def test_successful_admin_login_redirects(self, client, admin_user):
        """Test that admin login redirects to admin dashboard."""
        response = client.post(
            "/login",
            data={"email": "admin@test.com", "password": "adminpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/admin/dashboard" in response.location

    def test_successful_teacher_login_redirects(self, client, teacher_user):
        """Test that teacher login redirects to teacher dashboard."""
        response = client.post(
            "/login",
            data={"email": "teacher@test.com", "password": "teacherpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/teacher/dashboard" in response.location

    def test_successful_student_login_redirects(self, client, student_user):
        """Test that student login redirects to student domains."""
        response = client.post(
            "/login",
            data={"email": "student@test.com", "password": "studentpass123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/student/domains" in response.location

    def test_failed_login_shows_error(self, client, admin_user):
        """Test that failed login shows error message."""
        response = client.post(
            "/login",
            data={"email": "admin@test.com", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Invalid email or password" in response.data

    def test_logout_clears_session(self, authenticated_admin):
        """Test that logout clears the session."""
        # Verify logged in by accessing protected route
        response = authenticated_admin.get("/admin/dashboard")
        assert response.status_code == 200

        # Logout
        response = authenticated_admin.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location

        # Try to access protected route again - should be denied
        response = authenticated_admin.get("/admin/dashboard", follow_redirects=False)
        # After logout, should get 302 (redirect) or 403 (forbidden) - both valid
        assert response.status_code in [302, 403]


class TestPasswordSetup:
    """Test token-based password setup."""

    def test_setup_password_page_loads(self, app, client):
        """Test that setup password page loads with valid token."""
        with app.app_context():
            teacher = create_user(
                email="setuptest@test.com",
                password=None,
                role="teacher",
                first_name="Setup",
                last_name="Test",
                organization_id=1,
            )
            token = teacher.setup_token

        response = client.get(f"/setup-password/{token}")
        assert response.status_code == 200
        assert b"SET YOUR PASSWORD" in response.data

    def test_setup_password_success(self, app, client):
        """Test successful password setup."""
        with app.app_context():
            teacher = create_user(
                email="setuptest2@test.com",
                password=None,
                role="teacher",
                first_name="Setup",
                last_name="Test",
                organization_id=1,
            )
            token = teacher.setup_token

        response = client.post(
            f"/setup-password/{token}",
            data={"password": "newpassword123", "confirm_password": "newpassword123"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Password set successfully" in response.data

        # Verify can log in with new password
        with app.app_context():
            user = authenticate_user("setuptest2@test.com", "newpassword123")
            assert user is not None

    def test_setup_password_mismatch(self, app, client):
        """Test password setup with mismatched passwords."""
        with app.app_context():
            teacher = create_user(
                email="setuptest3@test.com",
                password=None,
                role="teacher",
                first_name="Setup",
                last_name="Test",
                organization_id=1,
            )
            token = teacher.setup_token

        response = client.post(
            f"/setup-password/{token}",
            data={
                "password": "newpassword123",
                "confirm_password": "differentpassword",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Passwords do not match" in response.data

    def test_invalid_token_fails(self, client):
        """Test that invalid setup token fails."""
        response = client.get("/setup-password/invalidtoken", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid setup link" in response.data
