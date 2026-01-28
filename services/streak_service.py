"""Streak tracking service for encouraging consistent daily practice."""

from datetime import date, timedelta
from models import db, User
from services.progress_service import get_questions_answered_today


def update_streak(user_id):
    """
    Update a user's streak when they answer a question.

    Called when a user answers a question. Logic:
    1. Get user's last_practice_date
    2. Get today's date (UTC)
    3. If last_practice_date == today: return (already counted)
    4. If last_practice_date == yesterday:
       - current_streak += 1
       - if current_streak > longest_streak: longest_streak = current_streak
    5. Else (missed a day or first time):
       - current_streak = 1
       - if longest_streak == 0: longest_streak = 1
    6. Set last_practice_date = today
    7. Commit changes

    Args:
        user_id: ID of the user
    """
    user = User.query.get(user_id)
    if not user:
        return

    today = date.today()
    yesterday = today - timedelta(days=1)

    # If already practiced today, no change needed
    if user.last_practice_date == today:
        return

    # Determine new streak value
    if user.last_practice_date == yesterday:
        # Consecutive day - increment streak
        user.current_streak += 1
        if user.current_streak > user.longest_streak:
            user.longest_streak = user.current_streak
    else:
        # Missed a day or first time - reset to 1
        user.current_streak = 1
        if user.longest_streak == 0:
            user.longest_streak = 1

    # Update last practice date
    user.last_practice_date = today

    db.session.commit()


def get_streak_info(user_id):
    """
    Get comprehensive streak information for a user.

    Args:
        user_id: ID of the user

    Returns:
        dict with:
        - current_streak: int
        - longest_streak: int
        - last_practice_date: date or None
        - daily_goal: int
        - questions_today: int
        - goal_completed: bool
        - goal_percentage: int (0-100)
        - streak_at_risk: bool (practiced yesterday but not today yet)
    """
    user = User.query.get(user_id)
    if not user:
        return None

    questions_today = get_questions_answered_today(user_id)
    goal_percentage = min(100, int((questions_today / user.daily_goal) * 100))

    return {
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
        "last_practice_date": user.last_practice_date,
        "daily_goal": user.daily_goal,
        "questions_today": questions_today,
        "goal_completed": questions_today >= user.daily_goal,
        "goal_percentage": goal_percentage,
        "streak_at_risk": is_streak_at_risk(user_id),
    }


def is_streak_at_risk(user_id):
    """
    Check if a user's streak is at risk.

    Returns True if user practiced yesterday but hasn't practiced today yet.
    Used for UI warning.

    Args:
        user_id: ID of the user

    Returns:
        bool: True if streak is at risk
    """
    user = User.query.get(user_id)
    if not user:
        return False

    # No streak to risk if they never practiced or have no streak
    if user.last_practice_date is None or user.current_streak == 0:
        return False

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Streak at risk if last practice was yesterday (not today)
    return user.last_practice_date == yesterday


def get_daily_goal_progress(user_id):
    """
    Get daily goal progress for a user.

    Args:
        user_id: ID of the user

    Returns:
        tuple: (questions_today, daily_goal, percentage)
    """
    user = User.query.get(user_id)
    if not user:
        return (0, 20, 0)

    questions_today = get_questions_answered_today(user_id)
    percentage = min(100, int((questions_today / user.daily_goal) * 100))

    return (questions_today, user.daily_goal, percentage)
