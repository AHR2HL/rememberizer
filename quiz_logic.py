"""Quiz generation and fact selection logic."""

import random
from datetime import datetime
from models import (
    Fact,
    FactState,
    get_mastered_facts,
    get_attempt_count,
    Domain,
    get_unlearned_facts,
    get_learned_facts,
    is_fact_learned,
)


def select_next_fact(domain_id, question_count):
    """
    Select the next fact to quiz based on learning state.

    Priority:
    1. If unlearned facts exist, return None (should show fact first, not quiz)
    2. Every 3rd question: select random mastered fact for reinforcement
    3. Otherwise: select learned (not mastered) least-practiced fact

    Args:
        domain_id: ID of the domain
        question_count: Current question number (0-indexed)

    Returns:
        Fact: The selected Fact object, or None if no learned facts to quiz
    """
    # Check for unlearned facts - don't quiz until shown
    unlearned = get_unlearned_facts(domain_id)
    if unlearned:
        return None  # Signal that we need to show a fact first

    # Reinforcement: every 3rd question, quiz mastered fact
    if question_count > 0 and question_count % 3 == 0:
        mastered = get_mastered_facts(domain_id)
        if mastered:
            return random.choice(mastered)

    # Select from learned (but not mastered) facts
    learned = get_learned_facts(domain_id)
    if not learned:
        # All facts are mastered or unlearned
        all_learned = Fact.query.filter_by(domain_id=domain_id).all()
        learned = [f for f in all_learned if is_fact_learned(f.id)]
        if not learned:
            return None  # No learned facts to quiz

    # Select least-practiced learned fact
    learned_with_counts = [(fact, get_attempt_count(fact.id)) for fact in learned]
    learned_with_counts.sort(key=lambda x: x[1])
    min_attempts = learned_with_counts[0][1]
    least_practiced = [
        fact for fact, count in learned_with_counts if count == min_attempts
    ]

    return random.choice(least_practiced)


def select_random_field(fact):
    """
    Select a random field from a fact to quiz.

    Args:
        fact: Fact object

    Returns:
        str: Name of the selected field
    """
    fact_data = fact.get_fact_data()
    fields = list(fact_data.keys())
    return random.choice(fields)


def get_identifying_field(fact, domain):
    """
    Get the first field of a fact for identification purposes.

    Typically the "name" or first field in the domain's field list.

    Args:
        fact: Fact object
        domain: Domain object

    Returns:
        tuple: (field_name, field_value)
    """
    field_names = domain.get_field_names()
    first_field = field_names[0]
    fact_data = fact.get_fact_data()
    return (first_field, fact_data[first_field])


def generate_question(fact, field_name, all_facts, domain):
    """
    Generate a multiple-choice question for a specific fact field.

    Args:
        fact: Fact object to quiz
        field_name: Name of the field to quiz
        all_facts: List of all Fact objects in the domain (for wrong answers)
        domain: Domain object (for identifying field)

    Returns:
        dict: Question data with keys:
            - question: Question text
            - options: List of answer options
            - correct_index: Index of correct answer in options
            - correct_answer: The correct answer text
    """
    fact_data = fact.get_fact_data()
    correct_answer = fact_data[field_name]

    # Get identifying field for question text
    id_field_name, id_field_value = get_identifying_field(fact, domain)

    # Generate question text
    question = f"What is the {field_name} of {id_field_value}?"

    # Collect wrong answers from other facts
    wrong_answers = []
    for other_fact in all_facts:
        if other_fact.id != fact.id:
            other_data = other_fact.get_fact_data()
            if field_name in other_data:
                answer = other_data[field_name]
                # Avoid duplicate answers
                if answer != correct_answer and answer not in wrong_answers:
                    wrong_answers.append(answer)

    # Handle case with fewer than 3 other facts
    if len(wrong_answers) < 3:
        # Add placeholder wrong answers if needed
        while len(wrong_answers) < 3:
            placeholder = f"Option {len(wrong_answers) + 1}"
            if placeholder not in wrong_answers and placeholder != correct_answer:
                wrong_answers.append(placeholder)

    # Select 3 random wrong answers
    if len(wrong_answers) > 3:
        wrong_answers = random.sample(wrong_answers, 3)

    # Combine correct and wrong answers
    options = [correct_answer] + wrong_answers

    # Shuffle options
    random.shuffle(options)

    # Find index of correct answer
    correct_index = options.index(correct_answer)

    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "correct_answer": correct_answer,
    }


def prepare_quiz_question(domain_id, question_count):
    """
    Prepare a complete quiz question for the next fact.

    Convenience function that selects fact, field, and generates question.

    Args:
        domain_id: ID of the domain
        question_count: Current question number

    Returns:
        dict: Question data with additional keys:
            - fact_id: ID of the quizzed fact
            - field_name: Name of the quizzed field
        Returns None if no facts available
    """
    # Select fact
    fact = select_next_fact(domain_id, question_count)
    if not fact:
        return None

    # Select field
    field_name = select_random_field(fact)

    # Get all facts in domain for wrong answers
    all_facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Get domain
    domain = Domain.query.get(domain_id)

    # Generate question
    question_data = generate_question(fact, field_name, all_facts, domain)

    # Add fact and field info
    question_data["fact_id"] = fact.id
    question_data["field_name"] = field_name

    return question_data


def get_next_unlearned_fact(domain_id):
    """
    Get the next unlearned fact to display.

    Returns the least-recently-shown unlearned fact, or None if all learned.

    Args:
        domain_id: ID of the domain

    Returns:
        Fact: The next unlearned Fact object, or None if all facts learned
    """
    unlearned = get_unlearned_facts(domain_id)
    if not unlearned:
        return None

    # Return least-recently-shown unlearned fact
    unlearned_with_times = []
    for fact in unlearned:
        state = FactState.query.filter_by(fact_id=fact.id).first()
        last_shown = state.last_shown_at if state else None
        unlearned_with_times.append((fact, last_shown))

    # Sort by last_shown_at (None first, then oldest first)
    unlearned_with_times.sort(key=lambda x: x[1] if x[1] else datetime.min)

    return unlearned_with_times[0][0]


def prepare_quiz_question_for_fact(fact, domain_id):
    """
    Prepare a quiz question for a specific fact.

    Args:
        fact: Fact object to quiz
        domain_id: ID of the domain

    Returns:
        dict: Question data with keys:
            - question: Question text
            - options: List of answer options
            - correct_index: Index of correct answer
            - fact_id: ID of the fact
            - field_name: Name of the quizzed field
        Returns None if fact is invalid
    """
    if not fact:
        return None

    # Select field
    field_name = select_random_field(fact)

    # Get all facts in domain for wrong answers
    all_facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Get domain
    domain = Domain.query.get(domain_id)

    # Generate question
    question_data = generate_question(fact, field_name, all_facts, domain)

    # Add fact and field info
    question_data["fact_id"] = fact.id
    question_data["field_name"] = field_name

    return question_data
