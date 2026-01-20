"""Doom loop detection and recovery logic."""

from models import Attempt
from services.fact_service import get_learned_facts, get_mastery_status


def check_doom_loop_trigger(recent_attempts):
    """
    Check if user is in doom loop (3 out of last 4 wrong).

    Args:
        recent_attempts: List of recent attempt dictionaries with 'correct' key

    Returns:
        bool: True if doom loop should trigger (3 of 4 wrong), False otherwise
    """
    if len(recent_attempts) < 4:
        return False

    wrong_count = sum(1 for attempt in recent_attempts[-4:] if not attempt["correct"])
    return wrong_count >= 3


def select_recovery_fact(domain_id, excluded_fact_ids, user_id):
    """
    Select an appropriate fact for doom loop recovery.

    Criteria:
    - Must be learned (learned_at is not NULL)
    - Should not be mastered (not 6 of 7)
    - Exclude facts that recently caused failures
    - Prefer facts with higher success rate

    Args:
        domain_id: The current domain ID
        excluded_fact_ids: List of fact IDs to exclude (recent failures)
        user_id: ID of the user

    Returns:
        Fact: Selected fact for recovery, or None if no suitable facts
    """
    # Get all learned facts in domain for this user
    learned_facts = get_learned_facts(domain_id, user_id)

    if not learned_facts:
        # No learned facts available for recovery
        return None

    # Filter out mastered facts and excluded facts
    candidates = []
    for fact in learned_facts:
        if fact.id in excluded_fact_ids:
            continue
        if get_mastery_status(fact.id, user_id):
            continue
        candidates.append(fact)

    if not candidates:
        # Fallback: just use any learned fact (even if it was excluded)
        # This handles edge case where all learned facts were part of the doom loop
        for fact in learned_facts:
            if not get_mastery_status(fact.id, user_id):
                return fact
        # If all learned facts are mastered, just pick the first one
        return learned_facts[0] if learned_facts else None

    # Calculate success rates and prefer higher success
    fact_scores = []
    for fact in candidates:
        attempts = Attempt.query.filter_by(fact_id=fact.id, user_id=user_id).all()
        if not attempts:
            fact_scores.append((fact, 0.5))  # Neutral score
            continue
        correct_count = sum(1 for a in attempts if a.correct)
        success_rate = correct_count / len(attempts)
        fact_scores.append((fact, success_rate))

    # Sort by success rate descending and pick the best one
    fact_scores.sort(key=lambda x: x[1], reverse=True)
    return fact_scores[0][0]
