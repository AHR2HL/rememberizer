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
    2. Every 10th question: select random mastered fact for reinforcement
    3. Otherwise: select learned (not mastered) least-practiced fact

    Note: Per-fact review questions are handled in app.py routes.

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

    # Additional reinforcement: every 10th question, quiz mastered fact
    # (supplement to per-fact review in app.py)
    if question_count > 0 and question_count % 10 == 0:
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


def select_field_pair(fact):
    """
    Select two different fields for a question: one for context, one to quiz.

    Returns:
        tuple: (context_field, quiz_field) where context_field != quiz_field
    """
    fact_data = fact.get_fact_data()
    fields = list(fact_data.keys())

    if len(fields) < 2:
        raise ValueError(f"Fact {fact.id} needs at least 2 fields for quizzing")

    # Select two different fields
    context_field = random.choice(fields)
    remaining_fields = [f for f in fields if f != context_field]
    quiz_field = random.choice(remaining_fields)

    return context_field, quiz_field


def singularize_domain_name(domain_name):
    """
    Convert domain name to singular form using smart heuristics.

    Args:
        domain_name: Plural domain name (e.g., "Greek Muses", "Categories")

    Returns:
        str: Singularized domain name (e.g., "Greek Muse", "Category")

    Examples:
        "Greek Muses" -> "Greek Muse"
        "Categories" -> "Category"
        "Oxen" -> "Ox"
        "People" -> "Person"
    """
    # Split into words to preserve prefixes like "Greek"
    words = domain_name.split()

    # Singularize the last word only
    last_word = words[-1] if words else domain_name

    # Irregular plurals (most common cases)
    irregular = {
        "people": "person",
        "children": "child",
        "men": "man",
        "women": "woman",
        "teeth": "tooth",
        "feet": "foot",
        "mice": "mouse",
        "geese": "goose",
        "oxen": "ox",
    }

    last_word_lower = last_word.lower()
    if last_word_lower in irregular:
        # Preserve original capitalization
        singular = irregular[last_word_lower]
        if last_word[0].isupper():
            singular = singular.capitalize()
        words[-1] = singular
        return " ".join(words)

    # Pattern-based rules (in order of precedence)
    if last_word.endswith("ies") and len(last_word) > 3:
        # Categories -> Category, Stories -> Story
        words[-1] = last_word[:-3] + "y"
    elif last_word.endswith("ves") and len(last_word) > 3:
        # Wolves -> Wolf, Knives -> Knife
        words[-1] = last_word[:-3] + "f"
    elif last_word.endswith("xes") and len(last_word) > 3:
        # Boxes -> Box, Fixes -> Fix
        words[-1] = last_word[:-2]
    elif last_word.endswith("ches") or last_word.endswith("shes"):
        # Matches -> Match, Dishes -> Dish
        words[-1] = last_word[:-2]
    elif last_word.endswith("sses") and len(last_word) > 4:
        # Glasses -> Glass, Bosses -> Boss
        words[-1] = last_word[:-2]
    elif (
        last_word.endswith("ses")
        and len(last_word) > 3
        and not last_word[-4].lower() in "aeiou"
    ):
        # Bases -> Base, Vases -> Vase (consonant before "ses")
        words[-1] = last_word[:-2]
    elif last_word.endswith("s") and not last_word.endswith("ss"):
        # Default: just remove 's'
        # Planets -> Planet, Dogs -> Dog, Muses -> Muse
        # But preserve words like "Glass" -> "Glass"
        words[-1] = last_word[:-1]

    return " ".join(words)


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


def generate_question(fact, context_field, quiz_field, all_facts, domain):
    """
    Generate a multiple-choice question connecting two fields.

    Args:
        fact: Fact object to quiz
        context_field: Field to use as context in question
        quiz_field: Field to quiz (the answer)
        all_facts: List of all Fact objects (for wrong answers)
        domain: Domain object

    Returns:
        dict: Question data with question, options, correct_index, correct_answer
    """
    fact_data = fact.get_fact_data()
    context_value = fact_data[context_field]
    correct_answer = fact_data[quiz_field]

    field_names = domain.get_field_names()
    identifying_field = field_names[0]  # Usually "name"

    # Generate question text based on which fields are being used
    if context_field == identifying_field:
        # Context is name: "What is the symbol of Erato?"
        question = f"What is the {quiz_field} of {context_value}?"
    elif quiz_field == identifying_field:
        # Quiz is name: "Which muse has Lyre as their symbol?"
        domain_name = domain.name if hasattr(domain, "name") else "item"
        domain_singular = singularize_domain_name(domain_name).lower()
        question = (
            f"Which {domain_singular} has {context_value} as their {context_field}?"
        )
    else:
        # Neither is name: "What is domain of Greek Muse with symbol=Lyre?"
        domain_name = domain.name if hasattr(domain, "name") else "item"
        domain_singular = singularize_domain_name(domain_name).lower()
        question = (
            f"What is the {quiz_field} of the {domain_singular} "
            f"with {context_field} = {context_value}?"
        )

    # Collect wrong answers from quiz_field
    wrong_answers = []
    for other_fact in all_facts:
        if other_fact.id != fact.id:
            other_data = other_fact.get_fact_data()
            if quiz_field in other_data:
                answer = other_data[quiz_field]
                if answer != correct_answer and answer not in wrong_answers:
                    wrong_answers.append(answer)

    # Handle case with fewer than 3 wrong answers
    if len(wrong_answers) < 3:
        while len(wrong_answers) < 3:
            placeholder = f"Option {len(wrong_answers) + 1}"
            if placeholder not in wrong_answers and placeholder != correct_answer:
                wrong_answers.append(placeholder)

    # Select 3 random wrong answers
    if len(wrong_answers) > 3:
        wrong_answers = random.sample(wrong_answers, 3)

    # Combine and shuffle
    options = [correct_answer] + wrong_answers
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    return {
        "question": question,
        "options": options,
        "correct_index": correct_index,
        "correct_answer": correct_answer,
    }


def prepare_quiz_question(domain_id, question_count, last_question_key=None):
    """
    Prepare a complete quiz question for the next fact.

    Convenience function that selects fact, field, and generates question.

    Args:
        domain_id: ID of the domain
        question_count: Current question number
        last_question_key: Optional last question key to avoid duplicate

    Returns:
        dict: Question data with additional keys:
            - fact_id: ID of the quizzed fact
            - context_field: Field used as context
            - quiz_field: Field being quizzed
        Returns None if no facts available
    """
    # Select fact
    fact = select_next_fact(domain_id, question_count)
    if not fact:
        return None

    # Get all facts in domain for wrong answers
    all_facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Get domain
    domain = Domain.query.get(domain_id)

    # Try to select field pair different from last question
    max_retries = 10
    context_field = None
    quiz_field = None

    for attempt in range(max_retries):
        candidate_context, candidate_quiz = select_field_pair(fact)
        candidate_key = f"{fact.id}:{candidate_context}:{candidate_quiz}"

        if candidate_key != last_question_key or attempt == max_retries - 1:
            context_field = candidate_context
            quiz_field = candidate_quiz
            break

    # Generate question
    question_data = generate_question(
        fact, context_field, quiz_field, all_facts, domain
    )

    # Add fact and field info
    question_data["fact_id"] = fact.id
    question_data["context_field"] = context_field
    question_data["quiz_field"] = quiz_field

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


def prepare_quiz_question_for_fact(fact, domain_id, last_question_key=None):
    """
    Prepare quiz question for fact, avoiding duplicate if possible.

    Args:
        fact: Fact object to quiz
        domain_id: ID of the domain
        last_question_key: Optional last question key to avoid duplicate

    Returns:
        dict: Question data with keys:
            - question: Question text
            - options: List of answer options
            - correct_index: Index of correct answer
            - fact_id: ID of the fact
            - context_field: Field used as context
            - quiz_field: Field being quizzed
        Returns None if fact is invalid
    """
    if not fact:
        return None

    # Get all facts in domain for wrong answers
    all_facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Get domain
    domain = Domain.query.get(domain_id)

    # Try to select field pair different from last question
    max_retries = 10
    context_field = None
    quiz_field = None

    for attempt in range(max_retries):
        candidate_context, candidate_quiz = select_field_pair(fact)
        candidate_key = f"{fact.id}:{candidate_context}:{candidate_quiz}"

        if candidate_key != last_question_key or attempt == max_retries - 1:
            context_field = candidate_context
            quiz_field = candidate_quiz
            break

    # Generate question
    question_data = generate_question(
        fact, context_field, quiz_field, all_facts, domain
    )

    # Add fact and field info
    question_data["fact_id"] = fact.id
    question_data["context_field"] = context_field
    question_data["quiz_field"] = quiz_field

    return question_data
