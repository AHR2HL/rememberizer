"""Tests for database models and mastery logic."""

from models import (
    db,
    Domain,
    Fact,
    Attempt,
    FactState,
    get_mastery_status,
    get_mastered_facts,
    record_attempt,
    get_unmastered_facts,
    get_attempt_count,
    mark_fact_learned,
    mark_fact_shown,
    is_fact_learned,
    get_unlearned_facts,
    get_learned_facts,
    update_consecutive_attempts,
    has_two_consecutive_correct,
    reset_domain_progress,
    get_progress_string,
)


def test_domain_creation(app):
    """Test creating a domain."""
    with app.app_context():
        domain = Domain(name="Test Domain", filename="test.json")
        domain.set_field_names(["field1", "field2"])
        db.session.add(domain)
        db.session.commit()

        assert domain.id is not None
        assert domain.name == "Test Domain"
        assert domain.get_field_names() == ["field1", "field2"]


def test_fact_creation(app, populated_db):
    """Test creating a fact."""
    with app.app_context():
        fact = Fact.query.first()
        assert fact is not None
        assert fact.domain_id == populated_db.id

        fact_data = fact.get_fact_data()
        assert "name" in fact_data
        assert "category" in fact_data
        assert "value" in fact_data


def test_attempt_creation(app, populated_db, student_user):
    """Test creating an attempt."""
    with app.app_context():
        fact = Fact.query.first()
        attempt = Attempt(
            fact_id=fact.id, field_name="name", correct=True, user_id=student_user.id
        )
        db.session.add(attempt)
        db.session.commit()

        assert attempt.id is not None
        assert attempt.fact_id == fact.id
        assert attempt.correct is True


def test_mastery_status_no_attempts(app, populated_db, student_user):
    """Test mastery status with no attempts - should not be mastered."""
    with app.app_context():
        fact = Fact.query.first()
        assert get_mastery_status(fact.id, student_user.id) is False


def test_mastery_status_less_than_7_attempts(app, populated_db, student_user):
    """Test mastery status with less than 7 attempts - should not be mastered."""
    with app.app_context():
        fact = Fact.query.first()

        # Add 6 correct attempts
        for i in range(6):
            record_attempt(fact.id, "name", True, student_user.id)

        assert get_mastery_status(fact.id, student_user.id) is False


def test_mastery_status_6_of_7_correct_recent_correct(app, populated_db, student_user):
    """Test mastery status with 6 of 7 correct, most recent correct - mastered."""
    with app.app_context():
        fact = Fact.query.first()

        # Add 1 incorrect, then 6 correct
        record_attempt(fact.id, "name", False, student_user.id)
        for i in range(6):
            record_attempt(fact.id, "name", True, student_user.id)

        assert get_mastery_status(fact.id, student_user.id) is True


def test_mastery_status_6_of_7_correct_recent_incorrect(
    app, populated_db, student_user
):
    """Test mastery status with 6 of 7 correct, most recent incorrect - not mastered."""
    with app.app_context():
        fact = Fact.query.first()

        # Add 6 correct, then 1 incorrect
        for i in range(6):
            record_attempt(fact.id, "name", True, student_user.id)
        record_attempt(fact.id, "name", False, student_user.id)

        assert get_mastery_status(fact.id, student_user.id) is False


def test_mastery_status_7_of_7_correct(app, populated_db, student_user):
    """Test mastery status with 7 of 7 correct - mastered."""
    with app.app_context():
        fact = Fact.query.first()

        # Add 7 correct attempts
        for i in range(7):
            record_attempt(fact.id, "name", True, student_user.id)

        assert get_mastery_status(fact.id, student_user.id) is True


def test_mastery_status_multiple_fields(app, populated_db, student_user):
    """Test mastery status counts attempts across all fields."""
    with app.app_context():
        fact = Fact.query.first()

        # Add attempts for different fields
        record_attempt(fact.id, "name", False, student_user.id)
        record_attempt(fact.id, "category", True, student_user.id)
        record_attempt(fact.id, "value", True, student_user.id)
        record_attempt(fact.id, "name", True, student_user.id)
        record_attempt(fact.id, "category", True, student_user.id)
        record_attempt(fact.id, "value", True, student_user.id)
        record_attempt(fact.id, "name", True, student_user.id)

        # 6 of 7 correct, most recent correct = mastered
        assert get_mastery_status(fact.id, student_user.id) is True


def test_get_mastered_facts_none(app, populated_db, student_user):
    """Test get_mastered_facts with no mastered facts."""
    with app.app_context():
        mastered = get_mastered_facts(populated_db.id, student_user.id)
        assert len(mastered) == 0


def test_get_mastered_facts_some(app, populated_db, student_user):
    """Test get_mastered_facts with some mastered facts."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).limit(2).all()

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True, student_user.id)

        # Don't master second fact
        record_attempt(facts[1].id, "name", False, student_user.id)

        mastered = get_mastered_facts(populated_db.id, student_user.id)
        assert len(mastered) == 1
        assert mastered[0].id == facts[0].id


def test_record_attempt(app, populated_db, student_user):
    """Test recording an attempt."""
    with app.app_context():
        fact = Fact.query.first()
        attempt = record_attempt(fact.id, "name", True, student_user.id)

        assert attempt.id is not None
        assert attempt.fact_id == fact.id
        assert attempt.field_name == "name"
        assert attempt.correct is True

        # Verify it's in database
        retrieved = Attempt.query.get(attempt.id)
        assert retrieved is not None


def test_get_unmastered_facts(app, populated_db, student_user):
    """Test getting unmastered facts."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).limit(2).all()

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True, student_user.id)

        # Don't master second fact
        record_attempt(facts[1].id, "name", False, student_user.id)

        unmastered = get_unmastered_facts(populated_db.id, student_user.id)
        # Should have 4 unmastered (5 total - 1 mastered)
        assert len(unmastered) == 4
        assert facts[0].id not in [f.id for f in unmastered]


def test_get_attempt_count(app, populated_db, student_user):
    """Test getting attempt count for a fact."""
    with app.app_context():
        fact = Fact.query.first()

        assert get_attempt_count(fact.id, student_user.id) == 0

        record_attempt(fact.id, "name", True, student_user.id)
        assert get_attempt_count(fact.id, student_user.id) == 1

        record_attempt(fact.id, "category", False, student_user.id)
        assert get_attempt_count(fact.id, student_user.id) == 2


# FactState Tests


def test_fact_state_creation(app, populated_db, student_user):
    """Test creating a FactState."""
    with app.app_context():
        fact = Fact.query.first()
        state = FactState(fact_id=fact.id, user_id=student_user.id)
        db.session.add(state)
        db.session.commit()

        assert state.id is not None
        assert state.fact_id == fact.id
        assert state.learned_at is None
        assert state.consecutive_correct == 0
        assert state.consecutive_wrong == 0


def test_mark_fact_shown(app, populated_db, student_user):
    """Test marking a fact as shown."""
    with app.app_context():
        fact = Fact.query.first()
        state = mark_fact_shown(fact.id, student_user.id)

        assert state is not None
        assert state.last_shown_at is not None
        assert state.learned_at is None


def test_mark_fact_learned(app, populated_db, student_user):
    """Test marking a fact as learned."""
    with app.app_context():
        fact = Fact.query.first()
        state = mark_fact_learned(fact.id, student_user.id)

        assert state is not None
        assert state.learned_at is not None
        assert state.last_shown_at is not None


def test_is_fact_learned_unlearned(app, populated_db, student_user):
    """Test is_fact_learned with unlearned fact."""
    with app.app_context():
        fact = Fact.query.first()
        assert is_fact_learned(fact.id, student_user.id) is False


def test_is_fact_learned_learned(app, populated_db, student_user):
    """Test is_fact_learned with learned fact."""
    with app.app_context():
        fact = Fact.query.first()
        mark_fact_learned(fact.id, student_user.id)
        assert is_fact_learned(fact.id, student_user.id) is True


def test_get_unlearned_facts_all(app, populated_db, student_user):
    """Test get_unlearned_facts when all facts are unlearned."""
    with app.app_context():
        unlearned = get_unlearned_facts(populated_db.id, student_user.id)
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).count()
        assert len(unlearned) == all_facts


def test_get_unlearned_facts_some(app, populated_db, student_user):
    """Test get_unlearned_facts when some facts are learned."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).limit(2).all()

        # Mark first fact as learned
        mark_fact_learned(facts[0].id, student_user.id)

        unlearned = get_unlearned_facts(populated_db.id, student_user.id)
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).count()

        assert len(unlearned) == all_facts - 1
        assert facts[0].id not in [f.id for f in unlearned]


def test_get_learned_facts_none(app, populated_db, student_user):
    """Test get_learned_facts when no facts are learned."""
    with app.app_context():
        learned = get_learned_facts(populated_db.id, student_user.id)
        assert len(learned) == 0


def test_get_learned_facts_some(app, populated_db, student_user):
    """Test get_learned_facts with some learned facts."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).limit(2).all()

        # Mark first fact as learned but not mastered
        mark_fact_learned(facts[0].id, student_user.id)
        record_attempt(facts[0].id, "name", True, student_user.id)

        learned = get_learned_facts(populated_db.id, student_user.id)
        assert len(learned) == 1
        assert learned[0].id == facts[0].id


def test_update_consecutive_attempts_correct(app, populated_db, student_user):
    """Test update_consecutive_attempts with correct answer."""
    with app.app_context():
        fact = Fact.query.first()
        demoted = update_consecutive_attempts(fact.id, True, student_user.id)

        assert demoted is False
        state = FactState.query.filter_by(
            fact_id=fact.id, user_id=student_user.id
        ).first()
        assert state.consecutive_correct == 1
        assert state.consecutive_wrong == 0


def test_update_consecutive_attempts_wrong(app, populated_db, student_user):
    """Test update_consecutive_attempts with wrong answer."""
    with app.app_context():
        fact = Fact.query.first()
        demoted = update_consecutive_attempts(fact.id, False, student_user.id)

        assert demoted is False
        state = FactState.query.filter_by(
            fact_id=fact.id, user_id=student_user.id
        ).first()
        assert state.consecutive_correct == 0
        assert state.consecutive_wrong == 1


def test_update_consecutive_attempts_demotion(app, populated_db, student_user):
    """Test demotion to unlearned after 2 consecutive wrong."""
    with app.app_context():
        fact = Fact.query.first()

        # Mark as learned
        mark_fact_learned(fact.id, student_user.id)
        assert is_fact_learned(fact.id, student_user.id) is True

        # First wrong answer
        demoted = update_consecutive_attempts(fact.id, False, student_user.id)
        assert demoted is False

        # Second wrong answer - should demote
        demoted = update_consecutive_attempts(fact.id, False, student_user.id)
        assert demoted is True
        assert is_fact_learned(fact.id, student_user.id) is False


def test_has_two_consecutive_correct_false(app, populated_db, student_user):
    """Test has_two_consecutive_correct with less than 2 correct."""
    with app.app_context():
        fact = Fact.query.first()
        update_consecutive_attempts(fact.id, True, student_user.id)

        assert has_two_consecutive_correct(fact.id, student_user.id) is False


def test_has_two_consecutive_correct_true(app, populated_db, student_user):
    """Test has_two_consecutive_correct with 2+ correct."""
    with app.app_context():
        fact = Fact.query.first()
        update_consecutive_attempts(fact.id, True, student_user.id)
        update_consecutive_attempts(fact.id, True, student_user.id)

        assert has_two_consecutive_correct(fact.id, student_user.id) is True


def test_reset_domain_progress(app, populated_db, student_user):
    """Test resetting all progress for a domain."""
    with app.app_context():
        fact = Fact.query.first()

        # Add some progress
        mark_fact_learned(fact.id, student_user.id)
        record_attempt(fact.id, "name", True, student_user.id)

        # Verify progress exists
        assert (
            Attempt.query.filter_by(fact_id=fact.id, user_id=student_user.id).count()
            > 0
        )
        assert (
            FactState.query.filter_by(fact_id=fact.id, user_id=student_user.id).count()
            > 0
        )

        # Reset
        reset_domain_progress(populated_db.id, student_user.id)

        # Verify all progress cleared
        assert (
            Attempt.query.filter_by(fact_id=fact.id, user_id=student_user.id).count()
            == 0
        )
        assert (
            FactState.query.filter_by(fact_id=fact.id, user_id=student_user.id).count()
            == 0
        )


def test_get_progress_string_all_unlearned(app, populated_db, student_user):
    """Test progress string with all facts unlearned."""
    with app.app_context():
        progress = get_progress_string(populated_db.id, student_user.id)
        assert progress == "·····"  # 5 facts, all unlearned


def test_get_progress_string_mixed_states(app, populated_db, student_user):
    """Test progress string with facts in different states."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).order_by(Fact.id).all()

        # Fact 0: shown but not learned
        mark_fact_shown(facts[0].id, student_user.id)

        # Fact 1: learned but not mastered
        mark_fact_learned(facts[1].id, student_user.id)

        # Fact 2: mastered (7 correct attempts)
        mark_fact_learned(facts[2].id, student_user.id)
        for i in range(7):
            record_attempt(facts[2].id, "name", True, student_user.id)

        # Facts 3-4: unlearned

        progress = get_progress_string(populated_db.id, student_user.id)
        assert progress == "-+*··"


def test_get_progress_string_all_mastered(app, populated_db, student_user):
    """Test progress string with all facts mastered."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        for fact in facts:
            mark_fact_learned(fact.id, student_user.id)
            for i in range(7):
                record_attempt(fact.id, "name", True, student_user.id)

        progress = get_progress_string(populated_db.id, student_user.id)
        assert progress == "*****"


def test_get_progress_string_empty_domain(app):
    """Test progress string with non-existent domain."""
    with app.app_context():
        progress = get_progress_string(999)
        assert progress == ""
