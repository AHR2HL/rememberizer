"""Tests for quiz generation and fact selection logic."""

from quiz_logic import (
    select_next_fact,
    select_random_field,
    select_field_pair,
    get_identifying_field,
    generate_question,
    prepare_quiz_question,
    get_next_unlearned_fact,
    prepare_quiz_question_for_fact,
    singularize_domain_name,
)
from models import Fact, record_attempt, mark_fact_learned
import pytest


def test_select_next_fact_with_unlearned_returns_none(app, populated_db, student_user):
    """Test selecting next fact returns None when unlearned facts exist."""
    with app.app_context():
        # All facts are unlearned, should return None
        fact = select_next_fact(populated_db.id, 0, student_user.id)
        assert fact is None


def test_select_next_fact_returns_learned_not_mastered(app, populated_db, student_user):
    """Test selecting next fact returns learned (not mastered) fact."""
    with app.app_context():
        from models import get_mastery_status

        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in all_facts:
            mark_fact_learned(fact.id, student_user.id)

        facts = all_facts[:2]

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True, student_user.id)

        # Select next fact (not on reinforcement question)
        fact = select_next_fact(populated_db.id, 1, student_user.id)
        # Should be a learned but not mastered fact
        assert fact is not None
        assert fact.id != facts[0].id  # Should not be the mastered fact
        assert not get_mastery_status(
            fact.id, student_user.id
        )  # Should not be mastered


def test_select_next_fact_reinforcement_question(app, populated_db, student_user):
    """Test selecting mastered fact on every 10th question."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id, student_user.id)

        # Master first fact
        for i in range(7):
            record_attempt(facts[0].id, "name", True, student_user.id)

        # Question 10 should select mastered fact for reinforcement
        fact = select_next_fact(populated_db.id, 10, student_user.id)
        assert fact.id == facts[0].id


def test_select_next_fact_reinforcement_no_mastered(app, populated_db, student_user):
    """Test reinforcement question when no facts mastered yet."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id, student_user.id)

        # No mastered facts, should return a learned fact
        fact = select_next_fact(populated_db.id, 10, student_user.id)
        assert fact is not None


def test_select_next_fact_least_practiced(app, populated_db, student_user):
    """Test selecting least-practiced learned fact."""
    with app.app_context():
        from models import get_attempt_count

        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id, student_user.id)

        # Add some attempts to first two facts
        record_attempt(facts[0].id, "name", False, student_user.id)
        record_attempt(facts[1].id, "name", False, student_user.id)
        record_attempt(facts[1].id, "name", False, student_user.id)

        # Add attempts to all but one fact
        for fact in facts[2:-1]:
            record_attempt(fact.id, "name", False, student_user.id)

        # Last fact has no attempts, should be selected
        selected = select_next_fact(populated_db.id, 1, student_user.id)
        assert get_attempt_count(selected.id, student_user.id) == 0
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

        question_data = generate_question(
            fact, "name", "category", all_facts, populated_db
        )

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
        question_data = generate_question(fact1, "field1", "field2", all_facts, domain)

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
            question_data = generate_question(
                fact, "name", "category", all_facts, populated_db
            )
            correct_indices.append(question_data["correct_index"])

        # With shuffling, correct answer shouldn't always be at same index
        # (This test has a small chance of false negative, but very unlikely)
        assert len(set(correct_indices)) > 1


def test_prepare_quiz_question(app, populated_db, student_user):
    """Test preparing a complete quiz question."""
    with app.app_context():
        # Mark all facts as learned so quiz can proceed
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in all_facts:
            mark_fact_learned(fact.id, student_user.id)

        question_data = prepare_quiz_question(populated_db.id, 0, student_user.id)

        assert question_data is not None
        assert "question" in question_data
        assert "options" in question_data
        assert "correct_index" in question_data
        assert "fact_id" in question_data
        assert "context_field" in question_data
        assert "quiz_field" in question_data

        # Ensure context_field and quiz_field are different
        assert question_data["context_field"] != question_data["quiz_field"]

        # Verify fact exists
        fact = Fact.query.get(question_data["fact_id"])
        assert fact is not None
        assert fact.domain_id == populated_db.id


def test_prepare_quiz_question_no_facts(app, student_user):
    """Test preparing quiz question with no facts returns None."""
    with app.app_context():
        from models import Domain, db

        domain = Domain(name="Empty Domain", filename="empty.json")
        domain.set_field_names(["field1"])
        db.session.add(domain)
        db.session.commit()

        question_data = prepare_quiz_question(domain.id, 0, student_user.id)
        assert question_data is None


def test_get_next_unlearned_fact(app, populated_db, student_user):
    """Test getting next unlearned fact."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # All facts are unlearned
        next_fact = get_next_unlearned_fact(populated_db.id, student_user.id)
        assert next_fact is not None
        assert next_fact.domain_id == populated_db.id

        # Mark first fact as learned
        mark_fact_learned(facts[0].id, student_user.id)

        # Should still get an unlearned fact
        next_fact = get_next_unlearned_fact(populated_db.id, student_user.id)
        assert next_fact is not None
        assert next_fact.id != facts[0].id


def test_get_next_unlearned_fact_all_learned(app, populated_db, student_user):
    """Test getting next unlearned fact when all facts are learned."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id, student_user.id)

        # Should return None
        next_fact = get_next_unlearned_fact(populated_db.id, student_user.id)
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
        assert "context_field" in question_data
        assert "quiz_field" in question_data
        assert question_data["fact_id"] == fact.id

        # Ensure context_field and quiz_field are different
        assert question_data["context_field"] != question_data["quiz_field"]


def test_select_field_pair_returns_different_fields(app, populated_db):
    """Test that select_field_pair returns two different fields."""
    with app.app_context():
        fact = Fact.query.first()

        # Call select_field_pair multiple times
        for i in range(20):
            context_field, quiz_field = select_field_pair(fact)
            assert context_field != quiz_field

            # Verify both fields exist in fact
            fact_data = fact.get_fact_data()
            assert context_field in fact_data
            assert quiz_field in fact_data


def test_select_field_pair_with_two_fields(app):
    """Test select_field_pair with exactly 2 fields."""
    with app.app_context():
        from models import Domain, db

        domain = Domain(name="Two Field Domain", filename="two.json")
        domain.set_field_names(["name", "value"])
        db.session.add(domain)
        db.session.flush()

        fact = Fact(domain_id=domain.id)
        fact.set_fact_data({"name": "Test", "value": "123"})
        db.session.add(fact)
        db.session.commit()

        # Should return both possible combinations
        combinations = set()
        for i in range(20):
            context_field, quiz_field = select_field_pair(fact)
            assert context_field != quiz_field
            combinations.add((context_field, quiz_field))

        # Both combinations should appear: ("name", "value") or ("value", "name")
        assert len(combinations) == 2
        assert ("name", "value") in combinations or ("value", "name") in combinations


def test_select_field_pair_raises_with_single_field(app):
    """Test select_field_pair raises ValueError with only 1 field."""
    with app.app_context():
        from models import Domain, db

        domain = Domain(name="Single Field Domain", filename="single.json")
        domain.set_field_names(["name"])
        db.session.add(domain)
        db.session.flush()

        fact = Fact(domain_id=domain.id)
        fact.set_fact_data({"name": "Test"})
        db.session.add(fact)
        db.session.commit()

        # Should raise ValueError
        with pytest.raises(ValueError, match="needs at least 2 fields"):
            select_field_pair(fact)


def test_generate_question_bidirectional(app, populated_db):
    """Test generate_question supports bidirectional questions."""
    with app.app_context():
        fact = Fact.query.first()
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Test name -> category direction
        question_data1 = generate_question(
            fact, "name", "category", all_facts, populated_db
        )
        assert "question" in question_data1
        assert len(question_data1["options"]) == 4

        # Test category -> name direction
        question_data2 = generate_question(
            fact, "category", "name", all_facts, populated_db
        )
        assert "question" in question_data2
        assert len(question_data2["options"]) == 4

        # Both should be valid questions
        assert question_data1["question"] != question_data2["question"]


def test_prepare_quiz_question_avoids_consecutive_duplicate(
    app, populated_db, student_user
):
    """Test that prepare_quiz_question avoids consecutive duplicates."""
    with app.app_context():
        # Mark all facts as learned
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in all_facts:
            mark_fact_learned(fact.id, student_user.id)

        # Generate first question
        question_data1 = prepare_quiz_question(populated_db.id, 0, student_user.id)
        last_key = (
            f"{question_data1['fact_id']}:"
            f"{question_data1['context_field']}:"
            f"{question_data1['quiz_field']}"
        )

        # Generate second question with same fact (simulate pending fact scenario)
        # If the fact has more than 2 fields, it should avoid the duplicate
        fact = Fact.query.get(question_data1["fact_id"])
        fact_data = fact.get_fact_data()

        if len(fact_data) > 2:
            # Should generate different field pair
            different_count = 0
            for i in range(10):
                question_data2 = prepare_quiz_question_for_fact(
                    fact, populated_db.id, last_key
                )
                current_key = (
                    f"{question_data2['fact_id']}:"
                    f"{question_data2['context_field']}:"
                    f"{question_data2['quiz_field']}"
                )
                if current_key != last_key:
                    different_count += 1

            # Most should be different
            assert different_count > 5


def test_prepare_quiz_question_for_fact_with_last_question_key(app, populated_db):
    """Test passing last_question_key to prepare_quiz_question_for_fact."""
    with app.app_context():
        fact = Fact.query.first()
        fact_data = fact.get_fact_data()

        if len(fact_data) >= 3:
            # Generate question with last_question_key
            fields = list(fact_data.keys())
            last_key = f"{fact.id}:{fields[0]}:{fields[1]}"

            question_data = prepare_quiz_question_for_fact(
                fact, populated_db.id, last_key
            )

            assert question_data is not None

            # Should try to avoid the last key (though not guaranteed)
            # Just verify it returns valid data
            assert "question" in question_data
            assert "options" in question_data


def test_singularize_domain_name():
    """Test domain name singularization with various patterns."""
    # Simple plurals
    assert singularize_domain_name("Planets") == "Planet"
    assert singularize_domain_name("Dogs") == "Dog"

    # Pattern-based
    assert singularize_domain_name("Categories") == "Category"
    assert singularize_domain_name("Muses") == "Muse"
    assert singularize_domain_name("Greek Muses") == "Greek Muse"
    assert singularize_domain_name("Boxes") == "Box"
    assert singularize_domain_name("Matches") == "Match"

    # Irregular
    assert singularize_domain_name("People") == "Person"
    assert singularize_domain_name("Children") == "Child"
    assert singularize_domain_name("Oxen") == "Ox"

    # Edge cases
    assert singularize_domain_name("Glass") == "Glass"  # Don't remove 's' from 'ss'
    assert singularize_domain_name("Data") == "Data"  # Already singular


def test_generate_question_uses_domain_name(app, populated_db):
    """Test that questions use domain name instead of 'item'."""
    with app.app_context():
        fact = Fact.query.first()
        all_facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        fact_data = fact.get_fact_data()

        # Test case where neither field is identifying field
        # Domain name is "Test Domain"
        # Get two non-name fields if available
        fields = list(fact_data.keys())
        if len(fields) >= 3:
            # Use two non-name fields (assuming 'name' is the first field)
            non_name_fields = [f for f in fields if f != "name"]
            if len(non_name_fields) >= 2:
                question_data = generate_question(
                    fact,
                    non_name_fields[0],
                    non_name_fields[1],
                    all_facts,
                    populated_db,
                )

                # Should contain singularized domain name, NOT "item"
                assert "item" not in question_data["question"].lower()
                # Domain name "Test Domain" should appear
                assert "test domain" in question_data["question"].lower()
