"""Database models for the Rememberizer quiz app."""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Domain(db.Model):
    """Represents a fact domain (e.g., Greek Muses)."""

    __tablename__ = "domains"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    filename = db.Column(db.String(200), nullable=True)  # NULL for user-created domains
    field_names = db.Column(db.Text, nullable=False)  # JSON list of field names

    # Domain creation and visibility fields
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=True
    )
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    facts = db.relationship(
        "Fact", back_populates="domain", cascade="all, delete-orphan"
    )
    creator = db.relationship("User", foreign_keys=[created_by])
    organization = db.relationship("Organization", foreign_keys=[organization_id])

    def get_field_names(self):
        """Parse and return field names as a list."""
        return json.loads(self.field_names)

    def set_field_names(self, fields):
        """Store field names as JSON."""
        self.field_names = json.dumps(fields)


class Organization(db.Model):
    """Represents an organization (school, institution, etc.)."""

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    users = db.relationship("User", back_populates="organization")


class User(db.Model):
    """Represents a user (admin, teacher, or student)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(
        db.String(255), nullable=True
    )  # Nullable for new accounts
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'teacher', 'student'
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    setup_token = db.Column(
        db.String(100), nullable=True
    )  # For first-time password setup
    setup_token_expires = db.Column(db.DateTime, nullable=True)  # Token expiration

    # Streak tracking fields
    current_streak = db.Column(db.Integer, default=0, nullable=False)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)
    last_practice_date = db.Column(db.Date, nullable=True)  # Date only, not datetime
    daily_goal = db.Column(db.Integer, default=20, nullable=False)  # Questions per day

    organization = db.relationship("Organization", back_populates="users")
    domain_assignments = db.relationship(
        "UserDomainAssignment",
        foreign_keys="UserDomainAssignment.user_id",
        back_populates="user",
    )

    def get_full_name(self):
        """Return full name of user."""
        return f"{self.first_name} {self.last_name}"


class UserDomainAssignment(db.Model):
    """Represents assignment of a domain to a user (student)."""

    __tablename__ = "user_domain_assignments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey("domains.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "domain_id", name="uq_user_domain"),
    )

    user = db.relationship(
        "User", foreign_keys=[user_id], back_populates="domain_assignments"
    )
    domain = db.relationship("Domain")
    assigner = db.relationship("User", foreign_keys=[assigned_by])


class Fact(db.Model):
    """Represents a single fact within a domain."""

    __tablename__ = "facts"

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("domains.id"), nullable=False)
    fact_data = db.Column(db.Text, nullable=False)  # JSON object with all fields

    domain = db.relationship("Domain", back_populates="facts")
    attempts = db.relationship(
        "Attempt", back_populates="fact", cascade="all, delete-orphan"
    )

    def get_fact_data(self):
        """Parse and return fact data as a dict."""
        return json.loads(self.fact_data)

    def set_fact_data(self, data):
        """Store fact data as JSON."""
        self.fact_data = json.dumps(data)


class Attempt(db.Model):
    """Represents a quiz attempt on a specific fact field."""

    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    fact_id = db.Column(db.Integer, db.ForeignKey("facts.id"), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(50), nullable=True)

    fact = db.relationship("Fact", back_populates="attempts")
    user = db.relationship("User")


class FactState(db.Model):
    """Track learning state of facts."""

    __tablename__ = "fact_states"

    id = db.Column(db.Integer, primary_key=True)
    fact_id = db.Column(db.Integer, db.ForeignKey("facts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    learned_at = db.Column(db.DateTime, nullable=True)  # NULL = unlearned
    last_shown_at = db.Column(db.DateTime, nullable=True)
    consecutive_correct = db.Column(db.Integer, default=0)
    consecutive_wrong = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("fact_id", "user_id", name="uq_fact_user_state"),
    )

    fact = db.relationship("Fact", backref="state")
    user = db.relationship("User")
