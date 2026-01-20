"""Progress and statistics service for tracking student progress."""

from datetime import datetime
from models import db, User, Domain, Fact, FactState, Attempt
from services.fact_service import get_mastery_status, is_fact_learned, get_attempt_count
from services.domain_service import get_user_domains


def get_progress_string(domain_id, user_id):
    """
    Generate a progress string showing status of all facts in domain
    for a specific user.

    Returns a string of symbols (·-+*) representing fact states:
    · = unlearned (not shown)
    - = shown (but not learned)
    + = learned (but not mastered)
    * = mastered

    Args:
        domain_id: The domain ID
        user_id: ID of the user

    Returns:
        String of symbols, one per fact (e.g., "·-+*····")
    """
    # Get all facts for domain, ordered by ID for consistency
    domain = Domain.query.get(domain_id)
    if not domain:
        return ""

    facts = Fact.query.filter_by(domain_id=domain_id).order_by(Fact.id).all()

    progress_symbols = []
    for fact in facts:
        # Get fact state for this user
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()

        # Determine symbol based on state
        if not state or (state.learned_at is None and state.last_shown_at is None):
            # Unlearned - not shown yet
            symbol = "·"
        elif state.learned_at is None:
            # Shown but not learned
            symbol = "-"
        elif get_mastery_status(fact.id, user_id):
            # Mastered
            symbol = "*"
        else:
            # Learned but not mastered
            symbol = "+"

        progress_symbols.append(symbol)

    return "".join(progress_symbols)


def get_student_progress_summary(student_id):
    """
    Get a summary of a student's progress across all assigned domains.

    Args:
        student_id: ID of the student

    Returns:
        dict: Summary with domain progress information
    """
    student = User.query.get(student_id)
    if not student:
        return None

    # Get assigned domains
    domains = get_user_domains(student_id)

    summary = {
        "student": student,
        "domains": [],
        "total_domains": 0,
        "total_questions": 0,
    }

    for domain in domains:
        facts = Fact.query.filter_by(domain_id=domain.id).all()
        total_facts = len(facts)

        learned_count = len([f for f in facts if is_fact_learned(f.id, student_id)])
        mastered_count = len([f for f in facts if get_mastery_status(f.id, student_id)])

        # Get attempt count
        attempt_count = sum([get_attempt_count(f.id, student_id) for f in facts])

        # Get progress string
        progress_str = get_progress_string(domain.id, student_id)

        summary["domains"].append(
            {
                "domain": domain,
                "total_facts": total_facts,
                "learned_count": learned_count,
                "mastered_count": mastered_count,
                "attempt_count": attempt_count,
                "progress_string": progress_str,
            }
        )

        # Update summary totals
        summary["total_domains"] += 1
        summary["total_questions"] += attempt_count

    return summary


def get_student_domain_progress(student_id, domain_id):
    """
    Get detailed progress for a student in a specific domain.

    Args:
        student_id: ID of the student
        domain_id: ID of the domain

    Returns:
        dict: Detailed progress information
    """
    student = User.query.get(student_id)
    domain = Domain.query.get(domain_id)

    if not student or not domain:
        return None

    facts = Fact.query.filter_by(domain_id=domain_id).all()
    total_facts = len(facts)

    learned_count = len([f for f in facts if is_fact_learned(f.id, student_id)])
    mastered_count = len([f for f in facts if get_mastery_status(f.id, student_id)])
    attempt_count = sum([get_attempt_count(f.id, student_id) for f in facts])

    progress_str = get_progress_string(domain_id, student_id)

    # Get all attempts to calculate time spent
    all_attempts = []
    for fact in facts:
        attempts = Attempt.query.filter_by(fact_id=fact.id, user_id=student_id).all()
        all_attempts.extend(attempts)

    # Sort by timestamp
    all_attempts.sort(key=lambda a: a.timestamp)

    # Calculate time spent (rough estimate based on timestamps)
    time_spent_minutes = 0
    if len(all_attempts) > 1:
        first_attempt = all_attempts[0].timestamp
        last_attempt = all_attempts[-1].timestamp
        time_delta = last_attempt - first_attempt
        time_spent_minutes = int(time_delta.total_seconds() / 60)

    return {
        "student": student,
        "domain": domain,
        "total_facts": total_facts,
        "learned_count": learned_count,
        "mastered_count": mastered_count,
        "attempt_count": attempt_count,
        "time_spent_minutes": time_spent_minutes,
        "progress_string": progress_str,
    }


def get_questions_answered_today(user_id):
    """
    Get the number of questions answered by a user today.

    Args:
        user_id: ID of the user

    Returns:
        int: Number of attempts today
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    count = Attempt.query.filter(
        Attempt.user_id == user_id, Attempt.timestamp >= today_start
    ).count()

    return count


def get_total_time_spent(user_id):
    """
    Get total estimated time spent by a user across all domains.

    Args:
        user_id: ID of the user

    Returns:
        int: Total minutes spent (rough estimate)
    """
    attempts = (
        Attempt.query.filter_by(user_id=user_id).order_by(Attempt.timestamp).all()
    )

    if len(attempts) < 2:
        return 0

    # Calculate time from first to last attempt
    first_attempt = attempts[0].timestamp
    last_attempt = attempts[-1].timestamp
    time_delta = last_attempt - first_attempt
    total_minutes = int(time_delta.total_seconds() / 60)

    return total_minutes


def get_unique_session_count(user_id):
    """
    Get the number of unique quiz sessions for a user.

    Args:
        user_id: ID of the user

    Returns:
        int: Number of unique sessions
    """
    # Count distinct session_ids
    result = (
        db.session.query(Attempt.session_id)
        .filter(Attempt.user_id == user_id, Attempt.session_id.isnot(None))
        .distinct()
        .count()
    )

    return result


def format_time_spent(minutes):
    """
    Format minutes into a readable string.

    Args:
        minutes: Number of minutes

    Returns:
        str: Formatted time (e.g., "1h 30m", "45m")
    """
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h {remaining_minutes}m"
