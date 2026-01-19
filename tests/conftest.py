"""Shared test fixtures for pytest."""

import os
import tempfile
import pytest
from app import app as flask_app
from models import (
    db,
    Domain,
    Fact,
    User,
    Organization,
    UserDomainAssignment,
    FactState,
    Attempt,
    create_user,
    assign_domain_to_user,
)


@pytest.fixture(scope="function")
def app():
    """Create and configure a test Flask application."""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    # Create database tables
    with flask_app.app_context():
        db.create_all()

        # Create default organization for auth tests
        org = Organization(name="Test Organization")
        db.session.add(org)
        db.session.commit()
        org_id = org.id

    # Store org_id on the app for fixtures to use
    flask_app.config["TEST_ORG_ID"] = org_id

    yield flask_app

    # Cleanup
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Create a database session for tests."""
    with app.app_context():
        yield db


@pytest.fixture
def sample_facts():
    """Return sample fact data for testing."""
    return {
        "domain_name": "Test Domain",
        "fields": ["name", "category", "value"],
        "facts": [
            {"name": "Fact 1", "category": "Category A", "value": "Value 1"},
            {"name": "Fact 2", "category": "Category B", "value": "Value 2"},
            {"name": "Fact 3", "category": "Category C", "value": "Value 3"},
            {"name": "Fact 4", "category": "Category D", "value": "Value 4"},
            {"name": "Fact 5", "category": "Category E", "value": "Value 5"},
        ],
    }


@pytest.fixture
def populated_db(app, sample_facts):
    """Create a database populated with sample facts."""
    with app.app_context():
        # Create domain
        domain = Domain(name=sample_facts["domain_name"], filename="test.json")
        domain.set_field_names(sample_facts["fields"])
        db.session.add(domain)
        db.session.flush()

        # Create facts
        for fact_data in sample_facts["facts"]:
            fact = Fact(domain_id=domain.id)
            fact.set_fact_data(fact_data)
            db.session.add(fact)

        db.session.commit()

        yield domain


@pytest.fixture
def temp_facts_dir(tmp_path):
    """Create a temporary directory for fact JSON files."""
    facts_dir = tmp_path / "facts"
    facts_dir.mkdir()
    return facts_dir


# ============================================================================
# AUTH FIXTURES
# ============================================================================


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing."""
    with app.app_context():
        org_id = app.config["TEST_ORG_ID"]
        admin = create_user(
            email="admin@test.com",
            password="adminpass123",
            role="admin",
            first_name="Admin",
            last_name="User",
            organization_id=org_id,
        )
        db.session.commit()
        # Refresh to get updated attributes
        db.session.refresh(admin)
        return admin


@pytest.fixture
def teacher_user(app, admin_user):
    """Create a teacher user for testing."""
    with app.app_context():
        org_id = app.config["TEST_ORG_ID"]
        teacher = create_user(
            email="teacher@test.com",
            password="teacherpass123",
            role="teacher",
            first_name="Teacher",
            last_name="User",
            organization_id=org_id,
            created_by_id=admin_user.id,
        )
        db.session.commit()
        db.session.refresh(teacher)
        return teacher


@pytest.fixture
def student_user(app, teacher_user):
    """Create a student user for testing."""
    with app.app_context():
        org_id = app.config["TEST_ORG_ID"]
        student = create_user(
            email="student@test.com",
            password="studentpass123",
            role="student",
            first_name="Student",
            last_name="User",
            organization_id=org_id,
            created_by_id=teacher_user.id,
        )
        db.session.commit()
        db.session.refresh(student)
        return student


@pytest.fixture
def second_student(app, teacher_user):
    """Create a second student user for isolation testing."""
    with app.app_context():
        org_id = app.config["TEST_ORG_ID"]
        student = create_user(
            email="student2@test.com",
            password="studentpass123",
            role="student",
            first_name="Second",
            last_name="Student",
            organization_id=org_id,
            created_by_id=teacher_user.id,
        )
        db.session.commit()
        db.session.refresh(student)
        return student


@pytest.fixture
def authenticated_admin(client, admin_user):
    """Return a client authenticated as admin."""
    client.post(
        "/login",
        data={"email": "admin@test.com", "password": "adminpass123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def authenticated_teacher(client, teacher_user):
    """Return a client authenticated as teacher."""
    client.post(
        "/login",
        data={"email": "teacher@test.com", "password": "teacherpass123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def authenticated_student(client, student_user):
    """Return a client authenticated as student."""
    client.post(
        "/login",
        data={"email": "student@test.com", "password": "studentpass123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def assigned_domain(app, student_user, populated_db, teacher_user):
    """Assign test domain to student."""
    with app.app_context():
        assign_domain_to_user(student_user.id, populated_db.id, teacher_user.id)
        db.session.commit()
        return populated_db


@pytest.fixture
def user_with_progress(app, student_user, assigned_domain):
    """Create a student with some quiz progress."""
    with app.app_context():
        from models import mark_fact_learned, record_attempt

        # Get facts
        facts = Fact.query.filter_by(domain_id=assigned_domain.id).limit(3).all()

        # Mark first two as learned
        for fact in facts[:2]:
            mark_fact_learned(fact.id, student_user.id)

            # Record some attempts
            record_attempt(fact.id, "name", True, student_user.id, "session1")
            record_attempt(fact.id, "category", True, student_user.id, "session1")

        # Record one wrong attempt for third fact
        record_attempt(facts[2].id, "name", False, student_user.id, "session1")

        db.session.commit()
        return student_user
