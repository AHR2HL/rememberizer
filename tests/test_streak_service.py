"""Tests for the streak tracking service."""

from datetime import date, timedelta
from models import db, User
from services.streak_service import (
    update_streak,
    get_streak_info,
    is_streak_at_risk,
    get_daily_goal_progress,
)


class TestUpdateStreak:
    """Tests for the update_streak function."""

    def test_first_practice_starts_streak_at_one(self, app, student_user):
        """First ever practice should start streak at 1."""
        with app.app_context():
            user = User.query.get(student_user.id)
            assert user.current_streak == 0
            assert user.longest_streak == 0
            assert user.last_practice_date is None

            update_streak(student_user.id)

            user = User.query.get(student_user.id)
            assert user.current_streak == 1
            assert user.longest_streak == 1
            assert user.last_practice_date == date.today()

    def test_consecutive_days_increment_streak(self, app, student_user):
        """Practicing on consecutive days should increment streak."""
        with app.app_context():
            user = User.query.get(student_user.id)
            yesterday = date.today() - timedelta(days=1)

            # Set up: user practiced yesterday with streak of 3
            user.last_practice_date = yesterday
            user.current_streak = 3
            user.longest_streak = 5
            db.session.commit()

            # Practice today
            update_streak(student_user.id)

            user = User.query.get(student_user.id)
            assert user.current_streak == 4
            assert user.longest_streak == 5  # Didn't beat longest
            assert user.last_practice_date == date.today()

    def test_consecutive_days_updates_longest_streak(self, app, student_user):
        """When current streak exceeds longest, longest should update."""
        with app.app_context():
            user = User.query.get(student_user.id)
            yesterday = date.today() - timedelta(days=1)

            # Set up: user practiced yesterday with streak of 5 (equals longest)
            user.last_practice_date = yesterday
            user.current_streak = 5
            user.longest_streak = 5
            db.session.commit()

            # Practice today
            update_streak(student_user.id)

            user = User.query.get(student_user.id)
            assert user.current_streak == 6
            assert user.longest_streak == 6  # Updated to new record

    def test_missed_day_resets_streak(self, app, student_user):
        """Missing a day should reset streak to 1."""
        with app.app_context():
            user = User.query.get(student_user.id)
            three_days_ago = date.today() - timedelta(days=3)

            # Set up: user last practiced 3 days ago
            user.last_practice_date = three_days_ago
            user.current_streak = 10
            user.longest_streak = 15
            db.session.commit()

            # Practice today (missed 2 days)
            update_streak(student_user.id)

            user = User.query.get(student_user.id)
            assert user.current_streak == 1
            assert user.longest_streak == 15  # Longest unchanged
            assert user.last_practice_date == date.today()

    def test_same_day_no_change(self, app, student_user):
        """Multiple practices on same day should not change streak."""
        with app.app_context():
            user = User.query.get(student_user.id)

            # Set up: user already practiced today
            user.last_practice_date = date.today()
            user.current_streak = 5
            user.longest_streak = 5
            db.session.commit()

            # Practice again today
            update_streak(student_user.id)

            user = User.query.get(student_user.id)
            assert user.current_streak == 5  # No change
            assert user.longest_streak == 5  # No change
            assert user.last_practice_date == date.today()

    def test_nonexistent_user(self, app):
        """Updating streak for nonexistent user should not raise error."""
        with app.app_context():
            # Should not raise
            update_streak(99999)


class TestGetStreakInfo:
    """Tests for the get_streak_info function."""

    def test_get_streak_info_basic(self, app, student_user):
        """Test basic streak info retrieval."""
        with app.app_context():
            user = User.query.get(student_user.id)
            user.current_streak = 7
            user.longest_streak = 14
            user.daily_goal = 25
            db.session.commit()

            info = get_streak_info(student_user.id)

            assert info["current_streak"] == 7
            assert info["longest_streak"] == 14
            assert info["daily_goal"] == 25
            assert info["questions_today"] == 0
            assert info["goal_completed"] is False
            assert info["goal_percentage"] == 0

    def test_get_streak_info_with_progress(self, app, user_with_progress):
        """Test streak info with some practice progress."""
        with app.app_context():
            info = get_streak_info(user_with_progress.id)

            # Should have questions answered from the fixture
            assert info["questions_today"] >= 0
            assert "goal_percentage" in info

    def test_get_streak_info_nonexistent_user(self, app):
        """Test streak info for nonexistent user returns None."""
        with app.app_context():
            info = get_streak_info(99999)
            assert info is None


class TestIsStreakAtRisk:
    """Tests for the is_streak_at_risk function."""

    def test_streak_at_risk_practiced_yesterday(self, app, student_user):
        """Streak should be at risk if practiced yesterday but not today."""
        with app.app_context():
            user = User.query.get(student_user.id)
            yesterday = date.today() - timedelta(days=1)

            user.last_practice_date = yesterday
            user.current_streak = 5
            db.session.commit()

            assert is_streak_at_risk(student_user.id) is True

    def test_no_risk_practiced_today(self, app, student_user):
        """No risk if already practiced today."""
        with app.app_context():
            user = User.query.get(student_user.id)

            user.last_practice_date = date.today()
            user.current_streak = 5
            db.session.commit()

            assert is_streak_at_risk(student_user.id) is False

    def test_no_risk_no_streak(self, app, student_user):
        """No risk if user has no streak."""
        with app.app_context():
            user = User.query.get(student_user.id)

            user.last_practice_date = None
            user.current_streak = 0
            db.session.commit()

            assert is_streak_at_risk(student_user.id) is False

    def test_no_risk_streak_already_broken(self, app, student_user):
        """No risk if streak was already broken (missed multiple days)."""
        with app.app_context():
            user = User.query.get(student_user.id)
            three_days_ago = date.today() - timedelta(days=3)

            user.last_practice_date = three_days_ago
            user.current_streak = 5
            db.session.commit()

            # Not at risk - streak is already broken
            assert is_streak_at_risk(student_user.id) is False

    def test_no_risk_nonexistent_user(self, app):
        """No risk for nonexistent user."""
        with app.app_context():
            assert is_streak_at_risk(99999) is False


class TestGetDailyGoalProgress:
    """Tests for the get_daily_goal_progress function."""

    def test_daily_goal_progress_no_activity(self, app, student_user):
        """Test daily goal with no activity today."""
        with app.app_context():
            user = User.query.get(student_user.id)
            user.daily_goal = 20
            db.session.commit()

            questions, goal, percentage = get_daily_goal_progress(student_user.id)

            assert questions == 0
            assert goal == 20
            assert percentage == 0

    def test_daily_goal_progress_caps_at_100(self, app, student_user, assigned_domain):
        """Test that percentage caps at 100 even if goal exceeded."""
        with app.app_context():
            from services.fact_service import record_attempt
            from models import Fact

            user = User.query.get(student_user.id)
            user.daily_goal = 5  # Low goal
            db.session.commit()

            # Record more attempts than goal
            facts = Fact.query.filter_by(domain_id=assigned_domain.id).all()
            for i in range(10):
                record_attempt(facts[0].id, "name", True, student_user.id, "test")

            questions, goal, percentage = get_daily_goal_progress(student_user.id)

            assert questions == 10
            assert goal == 5
            assert percentage == 100  # Capped at 100

    def test_daily_goal_progress_nonexistent_user(self, app):
        """Test daily goal for nonexistent user returns defaults."""
        with app.app_context():
            questions, goal, percentage = get_daily_goal_progress(99999)

            assert questions == 0
            assert goal == 20  # Default
            assert percentage == 0
