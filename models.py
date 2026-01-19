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
    filename = db.Column(db.String(200), nullable=False)
    field_names = db.Column(db.Text, nullable=False)  # JSON list of field names

    facts = db.relationship(
        "Fact", back_populates="domain", cascade="all, delete-orphan"
    )

    def get_field_names(self):
        """Parse and return field names as a list."""
        return json.loads(self.field_names)

    def set_field_names(self, fields):
        """Store field names as JSON."""
        self.field_names = json.dumps(fields)


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

    fact = db.relationship("Fact", back_populates="attempts")


class FactState(db.Model):
    """Track learning state of facts."""

    __tablename__ = "fact_states"

    id = db.Column(db.Integer, primary_key=True)
    fact_id = db.Column(db.Integer, db.ForeignKey("facts.id"), nullable=False)
    learned_at = db.Column(db.DateTime, nullable=True)  # NULL = unlearned
    last_shown_at = db.Column(db.DateTime, nullable=True)
    consecutive_correct = db.Column(db.Integer, default=0)
    consecutive_wrong = db.Column(db.Integer, default=0)

    fact = db.relationship("Fact", backref="state")


def get_mastery_status(fact_id):
    """
    Check if a fact is mastered.

    Mastery = 6 of last 7 attempts correct AND most recent attempt correct.

    Args:
        fact_id: ID of the fact to check

    Returns:
        bool: True if fact is mastered, False otherwise
    """
    # Get last 7 attempts for this fact, ordered by timestamp descending
    attempts = (
        Attempt.query.filter_by(fact_id=fact_id)
        .order_by(Attempt.timestamp.desc())
        .limit(7)
        .all()
    )

    # Need at least 7 attempts to be mastered
    if len(attempts) < 7:
        return False

    # Most recent attempt must be correct
    if not attempts[0].correct:
        return False

    # Count correct attempts in last 7
    correct_count = sum(1 for attempt in attempts if attempt.correct)

    # Need at least 6 correct
    return correct_count >= 6


def get_mastered_facts(domain_id):
    """
    Get all mastered facts in a domain.

    Args:
        domain_id: ID of the domain

    Returns:
        list: List of Fact objects that are mastered
    """
    # Get all facts in domain
    facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Filter to only mastered facts
    mastered = [fact for fact in facts if get_mastery_status(fact.id)]

    return mastered


def record_attempt(fact_id, field_name, correct):
    """
    Record a quiz attempt.

    Args:
        fact_id: ID of the fact that was quizzed
        field_name: Name of the field that was quizzed
        correct: Boolean indicating if answer was correct

    Returns:
        Attempt: The created Attempt object
    """
    attempt = Attempt(fact_id=fact_id, field_name=field_name, correct=correct)
    db.session.add(attempt)
    db.session.commit()
    return attempt


def get_unmastered_facts(domain_id):
    """
    Get all unmastered facts in a domain.

    Args:
        domain_id: ID of the domain

    Returns:
        list: List of Fact objects that are not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unmastered = [fact for fact in facts if not get_mastery_status(fact.id)]
    return unmastered


def get_attempt_count(fact_id):
    """
    Get the total number of attempts for a fact.

    Args:
        fact_id: ID of the fact

    Returns:
        int: Number of attempts
    """
    return Attempt.query.filter_by(fact_id=fact_id).count()


def mark_fact_learned(fact_id):
    """
    Mark fact as learned when user views it and clicks Continue.

    Args:
        fact_id: ID of the fact to mark as learned

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id).first()
    if not state:
        state = FactState(fact_id=fact_id)
        db.session.add(state)
    state.learned_at = datetime.utcnow()
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def mark_fact_shown(fact_id):
    """
    Track when fact was displayed (before user clicks Continue).

    Args:
        fact_id: ID of the fact that was shown

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id).first()
    if not state:
        state = FactState(fact_id=fact_id)
        db.session.add(state)
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def is_fact_learned(fact_id):
    """
    Check if fact is in learned state.

    Args:
        fact_id: ID of the fact to check

    Returns:
        bool: True if learned (learned_at is not None), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id).first()
    return state is not None and state.learned_at is not None


def get_unlearned_facts(domain_id):
    """
    Get all unlearned facts in a domain.

    Args:
        domain_id: ID of the domain

    Returns:
        list: List of Fact objects that are unlearned
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unlearned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id).first()
        if not state or state.learned_at is None:
            unlearned.append(fact)
    return unlearned


def get_learned_facts(domain_id):
    """
    Get all learned (but not mastered) facts in a domain.

    Args:
        domain_id: ID of the domain

    Returns:
        list: List of Fact objects that are learned but not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    learned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id).first()
        if state and state.learned_at is not None and not get_mastery_status(fact.id):
            learned.append(fact)
    return learned


def update_consecutive_attempts(fact_id, correct):
    """
    Update consecutive correct/wrong counters.

    Args:
        fact_id: ID of the fact
        correct: Boolean indicating if attempt was correct

    Returns:
        bool: True if should demote to unlearned (2 consecutive wrong), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id).first()
    if not state:
        state = FactState(fact_id=fact_id, consecutive_correct=0, consecutive_wrong=0)
        db.session.add(state)
        db.session.flush()  # Flush to apply defaults

    if correct:
        state.consecutive_correct += 1
        state.consecutive_wrong = 0  # Reset wrong counter
    else:
        state.consecutive_wrong += 1
        state.consecutive_correct = 0  # Reset correct counter

        # Check if should demote to unlearned (2 consecutive wrong)
        if state.consecutive_wrong >= 2:
            state.learned_at = None  # Demote to unlearned
            state.consecutive_wrong = 0
            state.consecutive_correct = 0
            db.session.commit()
            return True  # Signal demotion

    db.session.commit()
    return False


def has_two_consecutive_correct(fact_id):
    """
    Check if fact has 2 consecutive correct answers.

    Args:
        fact_id: ID of the fact

    Returns:
        bool: True if fact has 2+ consecutive correct answers
    """
    state = FactState.query.filter_by(fact_id=fact_id).first()
    return state is not None and state.consecutive_correct >= 2


def reset_domain_progress(domain_id):
    """
    Reset all progress for a domain (learned status, attempts, mastery).

    Args:
        domain_id: ID of the domain to reset
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    for fact in facts:
        # Delete all attempts
        Attempt.query.filter_by(fact_id=fact.id).delete()
        # Delete fact state
        FactState.query.filter_by(fact_id=fact.id).delete()
    db.session.commit()
