"""Tests for quiz generation and fact selection logic."""

from quiz_logic import (
    select_next_fact,
    select_random_field,
    get_identifying_field,
    generate_question,
    prepare_quiz_question,
    get_next_unlearned_fact,
    prepare_quiz_question_for_fact,
)
from models import Fact, record_attempt, mark_fact_learned


def test_select_next_fact_with_unlearned_returns_none(app, populated_db):
    """Test selecting next fact returns None when unlearned facts exist."""
    with app.app_context():
        # All facts are unlearned, should return None
        fact = select_next_fact(populated_db.id, 0)
        assert fact is None


def test_select_next_fact_returns_learned_not_mastered(app, populated_db):
    """Test selecting next fact returns learned (not mastered) fact."""
    with app.app_context():
        from models import get_mastery_status

        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in all_facts:
            mark_fact_learned(fact.id)

        facts = all_facts[:2]

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True)

        # Select next fact (not on reinforcement question)
        fact = select_next_fact(populated_db.id, 1)
        # Should be a learned but not mastered fact
        assert fact is not None
        assert fact.id != facts[0].id  # Should not be the mastered fact
        assert not get_mastery_status(fact.id)  # Should not be mastered


def test_select_next_fact_reinforcement_question(app, populated_db):
    """Test selecting mastered fact on every 3rd question."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id)

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True)

        # Question 3 should select mastered fact for reinforcement
        fact = select_next_fact(populated_db.id, 3)
        assert fact.id == facts[0].id


def test_select_next_fact_reinforcement_no_mastered(app, populated_db):
    """Test reinforcement question when no facts mastered yet."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id)

        # No mastered facts, should return a learned fact
        fact = select_next_fact(populated_db.id, 3)
        assert fact is not None


def test_select_next_fact_least_practiced(app, populated_db):
    """Test selecting least-practiced learned fact."""
    with app.app_context():
        from models import get_attempt_count

        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id)

        # Add some attempts to first two facts
        record_attempt(facts[0].id, "name", False)
        record_attempt(facts[1].id, "name", False)
        record_attempt(facts[1].id, "name", False)

        # Add attempts to all but one fact
        for fact in facts[2:-1]:
            record_attempt(fact.id, "name", False)

        # Last fact has no attempts, should be selected
        selected = select_next_fact(populated_db.id, 1)
        assert get_attempt_count(selected.id) == 0
        assert selected.id == facts[-1].id


def test_select_random_field(app, populated_db):
    """Test selecting a random field from a fact."""
    with app.app_context():
        fact = Fact.query.first()
        field = select_random_field(fact)

        fact_data = fact.get_fact_data()
        assert field in fact_data


def test_get_identifying_field(app, populated_db):
    """Test getting the identifying field of a fact."""
    with app.app_context():
        fact = Fact.query.first()
        field_name, field_value = get_identifying_field(fact, populated_db)

        assert field_name == "name"  # First field in domain
        fact_data = fact.get_fact_data()
        assert field_value == fact_data["name"]


def test_generate_question(app, populated_db):
    """Test generating a multiple-choice question."""
    with app.app_context():
        fact = Fact.query.first()
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        question_data = generate_question(fact, "category", all_facts, populated_db)

        assert "question" in question_data
        assert "options" in question_data
        assert "correct_index" in question_data
        assert "correct_answer" in question_data

        # Should have 4 options
        assert len(question_data["options"]) == 4

        # Correct answer should be in options
        fact_data = fact.get_fact_data()
        assert fact_data["category"] in question_data["options"]

        # Correct index should point to correct answer
        correct_option = question_data["options"][question_data["correct_index"]]
        assert correct_option == question_data["correct_answer"]


def test_generate_question_with_few_facts(app):
    """Test generating question with less than 4 facts total."""
    with app.app_context():
        # Create domain with only 2 facts
        from models import Domain, db

        domain = Domain(name="Small Domain", filename="small.json")
        domain.set_field_names(["field1", "field2"])
        db.session.add(domain)
        db.session.flush()

        fact1 = Fact(domain_id=domain.id)
        fact1.set_fact_data({"field1": "A", "field2": "X"})
        db.session.add(fact1)

        fact2 = Fact(domain_id=domain.id)
        fact2.set_fact_data({"field1": "B", "field2": "Y"})
        db.session.add(fact2)

        db.session.commit()

        all_facts = Fact.query.filter_by(domain_id=domain.id).all()
        question_data = generate_question(fact1, "field2", all_facts, domain)

        # Should still have 4 options (with placeholders)
        assert len(question_data["options"]) == 4


def test_generate_question_shuffles_options(app, populated_db):
    """Test that question options are shuffled."""
    with app.app_context():
        fact = Fact.query.first()
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Generate multiple questions and check if options vary in position
        correct_indices = []
        for i in range(10):
            question_data = generate_question(fact, "category", all_facts, populated_db)
            correct_indices.append(question_data["correct_index"])

        # With shuffling, correct answer shouldn't always be at same index
        # (This test has a small chance of false negative, but very unlikely)
        assert len(set(correct_indices)) > 1


def test_prepare_quiz_question(app, populated_db):
    """Test preparing a complete quiz question."""
    with app.app_context():
        # Mark all facts as learned so quiz can proceed
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in all_facts:
            mark_fact_learned(fact.id)

        question_data = prepare_quiz_question(populated_db.id, 0)

        assert question_data is not None
        assert "question" in question_data
        assert "options" in question_data
        assert "correct_index" in question_data
        assert "fact_id" in question_data
        assert "field_name" in question_data

        # Verify fact exists
        fact = Fact.query.get(question_data["fact_id"])
        assert fact is not None
        assert fact.domain_id == populated_db.id


def test_prepare_quiz_question_no_facts(app):
    """Test preparing quiz question with no facts returns None."""
    with app.app_context():
        from models import Domain, db

        domain = Domain(name="Empty Domain", filename="empty.json")
        domain.set_field_names(["field1"])
        db.session.add(domain)
        db.session.commit()

        question_data = prepare_quiz_question(domain.id, 0)
        assert question_data is None


def test_get_next_unlearned_fact(app, populated_db):
    """Test getting next unlearned fact."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # All facts are unlearned
        next_fact = get_next_unlearned_fact(populated_db.id)
        assert next_fact is not None
        assert next_fact.domain_id == populated_db.id

        # Mark first fact as learned
        mark_fact_learned(facts[0].id)

        # Should still get an unlearned fact
        next_fact = get_next_unlearned_fact(populated_db.id)
        assert next_fact is not None
        assert next_fact.id != facts[0].id


def test_get_next_unlearned_fact_all_learned(app, populated_db):
    """Test getting next unlearned fact when all facts are learned."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id)

        # Should return None
        next_fact = get_next_unlearned_fact(populated_db.id)
        assert next_fact is None


def test_prepare_quiz_question_for_fact(app, populated_db):
    """Test preparing quiz question for a specific fact."""
    with app.app_context():
        fact = Fact.query.first()
        question_data = prepare_quiz_question_for_fact(fact, populated_db.id)

        assert question_data is not None
        assert "question" in question_data
        assert "options" in question_data
        assert "correct_index" in question_data
        assert "fact_id" in question_data
        assert "field_name" in question_data
        assert question_data["fact_id"] == fact.id
