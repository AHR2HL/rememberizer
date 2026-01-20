"""Fact-related business logic for the Rememberizer quiz app."""

from datetime import datetime
from models import db, Fact, FactState, Attempt


def get_mastery_status(fact_id, user_id):
    """
    Check if a fact is mastered for a specific user.

    Mastery = 6 of last 7 attempts correct AND most recent attempt correct.

    Args:
        fact_id: ID of the fact to check
        user_id: ID of the user

    Returns:
        bool: True if fact is mastered, False otherwise
    """
    # Get last 7 attempts for this fact by this user, ordered by timestamp descending
    attempts = (
        Attempt.query.filter_by(fact_id=fact_id, user_id=user_id)
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


def get_mastered_facts(domain_id, user_id):
    """
    Get all mastered facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are mastered
    """
    # Get all facts in domain
    facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Filter to only mastered facts
    mastered = [fact for fact in facts if get_mastery_status(fact.id, user_id)]

    return mastered


def record_attempt(fact_id, field_name, correct, user_id, session_id=None):
    """
    Record a quiz attempt.

    Args:
        fact_id: ID of the fact that was quizzed
        field_name: Name of the field that was quizzed
        correct: Boolean indicating if answer was correct
        user_id: ID of the user
        session_id: Optional session ID for engagement tracking

    Returns:
        Attempt: The created Attempt object
    """
    attempt = Attempt(
        fact_id=fact_id,
        field_name=field_name,
        correct=correct,
        user_id=user_id,
        session_id=session_id,
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def get_unmastered_facts(domain_id, user_id):
    """
    Get all unmastered facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unmastered = [fact for fact in facts if not get_mastery_status(fact.id, user_id)]
    return unmastered


def get_attempt_count(fact_id, user_id):
    """
    Get the total number of attempts for a fact by a specific user.

    Args:
        fact_id: ID of the fact
        user_id: ID of the user

    Returns:
        int: Number of attempts
    """
    return Attempt.query.filter_by(fact_id=fact_id, user_id=user_id).count()


def mark_fact_learned(fact_id, user_id):
    """
    Mark fact as learned when user views it and clicks Continue.

    Args:
        fact_id: ID of the fact to mark as learned
        user_id: ID of the user

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(fact_id=fact_id, user_id=user_id)
        db.session.add(state)
    state.learned_at = datetime.utcnow()
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def mark_fact_shown(fact_id, user_id):
    """
    Track when fact was displayed (before user clicks Continue).

    Args:
        fact_id: ID of the fact that was shown
        user_id: ID of the user

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(fact_id=fact_id, user_id=user_id)
        db.session.add(state)
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def is_fact_learned(fact_id, user_id):
    """
    Check if fact is in learned state for a specific user.

    Args:
        fact_id: ID of the fact to check
        user_id: ID of the user

    Returns:
        bool: True if learned (learned_at is not None), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    return state is not None and state.learned_at is not None


def get_unlearned_facts(domain_id, user_id):
    """
    Get all unlearned facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are unlearned
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unlearned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()
        if not state or state.learned_at is None:
            unlearned.append(fact)
    return unlearned


def get_learned_facts(domain_id, user_id):
    """
    Get all learned (but not mastered) facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are learned but not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    learned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()
        if (
            state
            and state.learned_at is not None
            and not get_mastery_status(fact.id, user_id)
        ):
            learned.append(fact)
    return learned


def update_consecutive_attempts(fact_id, correct, user_id):
    """
    Update consecutive correct/wrong counters for a specific user.

    Args:
        fact_id: ID of the fact
        correct: Boolean indicating if attempt was correct
        user_id: ID of the user

    Returns:
        bool: True if should demote to unlearned (2 consecutive wrong), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(
            fact_id=fact_id, user_id=user_id, consecutive_correct=0, consecutive_wrong=0
        )
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


def has_two_consecutive_correct(fact_id, user_id):
    """
    Check if fact has 2 consecutive correct answers for a specific user.

    Args:
        fact_id: ID of the fact
        user_id: ID of the user

    Returns:
        bool: True if fact has 2+ consecutive correct answers
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    return state is not None and state.consecutive_correct >= 2


def reset_domain_progress(domain_id, user_id):
    """
    Reset all progress for a domain for a specific user.
    Clears learned status, attempts, and mastery.

    Args:
        domain_id: ID of the domain to reset
        user_id: ID of the user
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    for fact in facts:
        # Delete all attempts by this user
        Attempt.query.filter_by(fact_id=fact.id, user_id=user_id).delete()
        # Delete fact state for this user
        FactState.query.filter_by(fact_id=fact.id, user_id=user_id).delete()
    db.session.commit()
