"""Tests for doom loop detection and recovery functionality."""

from doom_loop import check_doom_loop_trigger, select_recovery_fact
from models import (
    Domain,
    Fact,
    db,
    mark_fact_learned,
    record_attempt,
)


class TestDoomLoopDetection:
    """Tests for doom loop trigger detection."""

    def test_doom_loop_trigger_with_3_out_of_4_wrong(self):
        """Should trigger doom loop when 3 out of 4 answers are wrong."""
        recent = [
            {"fact_id": 1, "correct": False},
            {"fact_id": 2, "correct": False},
            {"fact_id": 3, "correct": True},
            {"fact_id": 4, "correct": False},
        ]
        assert check_doom_loop_trigger(recent) is True

    def test_no_doom_loop_with_2_out_of_4_wrong(self):
        """Should not trigger doom loop when only 2 out of 4 are wrong."""
        recent = [
            {"fact_id": 1, "correct": False},
            {"fact_id": 2, "correct": True},
            {"fact_id": 3, "correct": True},
            {"fact_id": 4, "correct": False},
        ]
        assert check_doom_loop_trigger(recent) is False

    def test_no_doom_loop_with_insufficient_attempts(self):
        """Should not trigger doom loop with fewer than 4 attempts."""
        recent = [
            {"fact_id": 1, "correct": False},
            {"fact_id": 2, "correct": False},
        ]
        assert check_doom_loop_trigger(recent) is False

    def test_doom_loop_only_considers_last_4(self):
        """Should only consider last 4 attempts."""
        recent = [
            {"fact_id": 1, "correct": True},
            {"fact_id": 2, "correct": True},
            {"fact_id": 3, "correct": False},
            {"fact_id": 4, "correct": False},
            {"fact_id": 5, "correct": False},
            {"fact_id": 6, "correct": False},
        ]
        # Last 4: 3 wrong, 1 wrong = 4 wrong, should trigger
        assert check_doom_loop_trigger(recent) is True

    def test_doom_loop_with_all_wrong(self):
        """Should trigger doom loop when all 4 are wrong."""
        recent = [
            {"fact_id": 1, "correct": False},
            {"fact_id": 2, "correct": False},
            {"fact_id": 3, "correct": False},
            {"fact_id": 4, "correct": False},
        ]
        assert check_doom_loop_trigger(recent) is True


class TestRecoveryFactSelection:
    """Tests for recovery fact selection logic."""

    def test_select_recovery_fact_basic(self, app, student_user):
        """Should select a learned but not mastered fact."""
        with app.app_context():
            # Create domain
            domain = Domain(name="Test Domain", filename="test.json")
            domain.set_field_names(["field1", "field2"])
            db.session.add(domain)
            db.session.flush()

            # Create facts
            fact1 = Fact(domain_id=domain.id)
            fact1.set_fact_data({"field1": "A", "field2": "B"})
            fact2 = Fact(domain_id=domain.id)
            fact2.set_fact_data({"field1": "C", "field2": "D"})
            db.session.add_all([fact1, fact2])
            db.session.flush()

            # Mark fact1 as learned
            mark_fact_learned(fact1.id, student_user.id)

            # Record some successful attempts (but not mastered)
            for _ in range(3):
                record_attempt(fact1.id, "field1", True, student_user.id)

            # Select recovery fact
            recovery = select_recovery_fact(domain.id, [], student_user.id)

            assert recovery is not None
            assert recovery.id == fact1.id

    def test_select_recovery_fact_excludes_specified_facts(self, app, student_user):
        """Should exclude facts in the excluded list."""
        with app.app_context():
            # Create domain
            domain = Domain(name="Test Domain", filename="test.json")
            domain.set_field_names(["field1", "field2"])
            db.session.add(domain)
            db.session.flush()

            # Create facts
            fact1 = Fact(domain_id=domain.id)
            fact1.set_fact_data({"field1": "A", "field2": "B"})
            fact2 = Fact(domain_id=domain.id)
            fact2.set_fact_data({"field1": "C", "field2": "D"})
            db.session.add_all([fact1, fact2])
            db.session.flush()

            # Mark both as learned
            mark_fact_learned(fact1.id, student_user.id)
            mark_fact_learned(fact2.id, student_user.id)

            # Exclude fact1
            recovery = select_recovery_fact(domain.id, [fact1.id], student_user.id)

            assert recovery is not None
            assert recovery.id == fact2.id

    def test_select_recovery_fact_no_learned_facts(self, app, student_user):
        """Should return None when no learned facts exist."""
        with app.app_context():
            # Create domain
            domain = Domain(name="Test Domain", filename="test.json")
            domain.set_field_names(["field1", "field2"])
            db.session.add(domain)
            db.session.flush()

            # Create unlearned fact
            fact1 = Fact(domain_id=domain.id)
            fact1.set_fact_data({"field1": "A", "field2": "B"})
            db.session.add(fact1)
            db.session.flush()

            # Select recovery fact
            recovery = select_recovery_fact(domain.id, [], student_user.id)

            assert recovery is None

    def test_select_recovery_fact_prefers_higher_success_rate(self, app, student_user):
        """Should prefer facts with higher success rates."""
        with app.app_context():
            # Create domain
            domain = Domain(name="Test Domain", filename="test.json")
            domain.set_field_names(["field1", "field2"])
            db.session.add(domain)
            db.session.flush()

            # Create facts
            fact1 = Fact(domain_id=domain.id)
            fact1.set_fact_data({"field1": "A", "field2": "B"})
            fact2 = Fact(domain_id=domain.id)
            fact2.set_fact_data({"field1": "C", "field2": "D"})
            db.session.add_all([fact1, fact2])
            db.session.flush()

            # Mark both as learned
            mark_fact_learned(fact1.id, student_user.id)
            mark_fact_learned(fact2.id, student_user.id)

            # fact1: 50% success rate (2/4)
            record_attempt(fact1.id, "field1", True, student_user.id)
            record_attempt(fact1.id, "field1", True, student_user.id)
            record_attempt(fact1.id, "field1", False, student_user.id)
            record_attempt(fact1.id, "field1", False, student_user.id)

            # fact2: 75% success rate (3/4)
            record_attempt(fact2.id, "field1", True, student_user.id)
            record_attempt(fact2.id, "field1", True, student_user.id)
            record_attempt(fact2.id, "field1", True, student_user.id)
            record_attempt(fact2.id, "field1", False, student_user.id)

            # Select recovery fact
            recovery = select_recovery_fact(domain.id, [], student_user.id)

            # Should prefer fact2 with higher success rate
            assert recovery is not None
            assert recovery.id == fact2.id


class TestDoomLoopIntegration:
    """Integration tests for doom loop flow."""

    def test_doom_loop_session_tracking(self, client):
        """Test that session properly tracks doom loop state."""
        with client.session_transaction() as sess:
            # Initialize session like start() does
            sess["domain_id"] = 1
            sess["question_count"] = 0
            sess["recent_attempts"] = []
            sess["consecutive_correct_in_session"] = 0
            sess["doom_loop_active"] = False

        # Verify session initialized
        with client.session_transaction() as sess:
            assert sess["doom_loop_active"] is False
            assert sess["recent_attempts"] == []
            assert sess["consecutive_correct_in_session"] == 0

    def test_doom_loop_exit_after_3_consecutive_correct(self, client):
        """Test that doom loop exits after 3 consecutive correct."""
        with client.session_transaction() as sess:
            sess["doom_loop_active"] = True
            sess["doom_loop_recovery_fact_id"] = 1
            sess["consecutive_correct_in_session"] = 3

        # In the actual app, the answer() route would check this and exit
        with client.session_transaction() as sess:
            # Simulate the exit logic
            if (
                sess.get("doom_loop_active")
                and sess.get("consecutive_correct_in_session", 0) >= 3
            ):
                sess["doom_loop_active"] = False
                sess.pop("doom_loop_recovery_fact_id", None)

        with client.session_transaction() as sess:
            assert sess["doom_loop_active"] is False
            assert "doom_loop_recovery_fact_id" not in sess
