"""Shared test fixtures for pytest."""

import os
import tempfile
import pytest
from app import app as flask_app
from models import db, Domain, Fact


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
