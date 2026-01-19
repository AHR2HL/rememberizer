"""Main Flask application for Rememberizer quiz app."""

import os
from flask import Flask, render_template, request, redirect, url_for, session
from models import (
    db,
    Domain,
    Fact,
    record_attempt,
    mark_fact_learned,
    mark_fact_shown,
    update_consecutive_attempts,
    has_two_consecutive_correct,
    reset_domain_progress,
)
from facts_loader import load_all_domains_from_directory, get_available_domains
from quiz_logic import (
    get_next_unlearned_fact,
    prepare_quiz_question_for_fact,
    select_next_fact,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Flag to track if database has been initialized
_db_initialized = False


@app.template_filter("center_in_box")
def center_in_box(text, width=35):
    """
    Center text within a fixed width for terminal box display.

    Args:
        text: The text to center
        width: The interior width of the box (default: 35)

    Returns:
        String with text centered using spaces, exactly 'width' characters long
    """
    if not text:
        text = ""

    # Convert to string and strip existing whitespace
    text = str(text).strip()

    # Use Python's built-in center method which handles padding automatically
    return text.center(width)


@app.template_filter("progress_string")
def progress_string_filter(domain_id):
    """Generate progress string for a domain."""
    from models import get_progress_string

    return get_progress_string(domain_id)


@app.template_filter("format_field_name")
def format_field_name_filter(field_name):
    """Format field name for display by replacing underscores with spaces."""
    return field_name.replace("_", " ")


@app.template_filter("singularize")
def singularize_filter(domain_name):
    """Singularize domain name for display."""
    from quiz_logic import singularize_domain_name

    return singularize_domain_name(domain_name)


def init_database():
    """Initialize database and load fact domains."""
    global _db_initialized
    if _db_initialized:
        return

    with app.app_context():
        db.create_all()
        # Load all JSON files from facts directory
        load_all_domains_from_directory("facts")
        _db_initialized = True


@app.before_request
def ensure_database():
    """Ensure database is initialized before first request."""
    init_database()


@app.route("/")
def index():
    """Display domain selection page."""
    domains = get_available_domains()
    return render_template("select_domain.html", domains=domains)


@app.route("/start", methods=["POST"])
def start():
    """Initialize quiz session with selected domain."""
    domain_id = request.form.get("domain_id", type=int)

    if not domain_id:
        return redirect(url_for("index"))

    domain = Domain.query.get(domain_id)
    if not domain:
        return redirect(url_for("index"))

    # Initialize session
    session["domain_id"] = domain_id
    session["question_count"] = 0

    # Get first unlearned fact to show
    next_fact = get_next_unlearned_fact(domain_id)
    if not next_fact:
        # No unlearned facts, start quizzing
        return redirect(url_for("quiz"))

    # Show first unlearned fact
    mark_fact_shown(next_fact.id)
    return redirect(url_for("show_fact", fact_id=next_fact.id))


@app.route("/show_fact/<int:fact_id>")
def show_fact(fact_id):
    """Display a fact in table format."""
    fact = Fact.query.get(fact_id)
    if not fact:
        return "Fact not found", 404

    domain = Domain.query.get(fact.domain_id)
    fact_data = fact.get_fact_data()
    field_names = domain.get_field_names()

    # Get highlight_field from query params (if user got question wrong)
    highlight_field = request.args.get("highlight_field", None)

    # Mark as shown (but not learned yet - that happens on continue)
    mark_fact_shown(fact_id)

    return render_template(
        "show_fact.html",
        fact=fact,
        fact_data=fact_data,
        field_names=field_names,
        domain=domain,
        highlight_field=highlight_field,
    )


@app.route("/mark_learned/<int:fact_id>", methods=["POST"])
def mark_learned(fact_id):
    """Mark fact as learned when user clicks Continue."""
    mark_fact_learned(fact_id)

    # Store that we need to quiz this fact next
    session["pending_quiz_fact_id"] = fact_id
    session["consecutive_correct_needed"] = 2

    return redirect(url_for("quiz"))


@app.route("/quiz")
def quiz():
    """Generate and display next quiz question."""
    domain_id = session.get("domain_id")
    question_count = session.get("question_count", 0)

    if not domain_id:
        return redirect(url_for("index"))

    # Increment question count BEFORE generating question
    # This ensures every question asked counts toward the total
    question_count += 1
    session["question_count"] = question_count

    # Check if we have a pending fact that needs 2 consecutive correct
    pending_fact_id = session.get("pending_quiz_fact_id")
    last_question_key = session.get("last_question_key")

    # Check for pending quiz fact (needs 2 consecutive correct)
    if pending_fact_id and not has_two_consecutive_correct(pending_fact_id):
        # Continue quizzing this fact until 2 consecutive correct
        fact = Fact.query.get(pending_fact_id)
        question_data = prepare_quiz_question_for_fact(
            fact, domain_id, last_question_key
        )

    # Check for pending review fact
    elif session.get("pending_review_fact_id"):
        review_fact_id = session.get("pending_review_fact_id")
        fact = Fact.query.get(review_fact_id)

        if fact:
            question_data = prepare_quiz_question_for_fact(
                fact, domain_id, last_question_key
            )
        else:
            # Review fact not found, clear flag and continue
            session.pop("pending_review_fact_id", None)
            session.pop("just_completed_fact_id", None)
            fact = select_next_fact(domain_id, question_count)
            if fact is None:
                next_unlearned = get_next_unlearned_fact(domain_id)
                if next_unlearned:
                    mark_fact_shown(next_unlearned.id)
                    return redirect(url_for("show_fact", fact_id=next_unlearned.id))
                else:
                    return "All facts mastered! Great job!", 200
            question_data = prepare_quiz_question_for_fact(
                fact, domain_id, last_question_key
            )

    # Normal fact selection
    else:
        # Clear pending fact if it exists
        if pending_fact_id:
            session.pop("pending_quiz_fact_id", None)

        # Select next fact
        fact = select_next_fact(domain_id, question_count)

        if fact is None:
            # No learned facts to quiz, show next unlearned fact
            next_unlearned = get_next_unlearned_fact(domain_id)
            if next_unlearned:
                mark_fact_shown(next_unlearned.id)
                return redirect(url_for("show_fact", fact_id=next_unlearned.id))
            else:
                return "All facts mastered! Great job!", 200

        question_data = prepare_quiz_question_for_fact(
            fact, domain_id, last_question_key
        )

    if not question_data:
        return "Error generating question", 400

    # Store current question data in session
    session["current_fact_id"] = question_data["fact_id"]
    session["current_field_name"] = question_data["quiz_field"]
    session["correct_index"] = question_data["correct_index"]
    session["correct_answer"] = question_data[
        "correct_answer"
    ]  # NEW: Store the actual answer value
    session["options"] = question_data[
        "options"
    ]  # NEW: Store all options to look up selected value
    fact_id = question_data["fact_id"]
    context = question_data["context_field"]
    quiz = question_data["quiz_field"]
    session["last_question_key"] = f"{fact_id}:{context}:{quiz}"

    domain = Domain.query.get(domain_id)

    return render_template(
        "quiz.html",
        question=question_data["question"],
        options=question_data["options"],
        domain=domain,
    )


@app.route("/answer", methods=["POST"])
def answer():
    """Process quiz answer and record attempt."""
    selected_index = request.form.get("answer", type=int)

    if selected_index is None:
        return "No answer provided", 400

    # Get session data
    fact_id = session.get("current_fact_id")
    field_name = session.get("current_field_name")
    correct_answer = session.get("correct_answer")  # NEW: Get the expected answer value
    options = session.get("options")  # NEW: Get the options list
    domain_id = session.get("domain_id")

    # Check if this was a review question
    is_review_question = fact_id == session.get("pending_review_fact_id")

    if (
        fact_id is None
        or field_name is None
        or correct_answer is None
        or options is None
    ):
        return redirect(url_for("index"))

    # Check if answer is correct by comparing VALUES, not indices
    # This handles the case where multiple facts have the same field value
    selected_answer = options[selected_index]
    is_correct = selected_answer == correct_answer

    # Record attempt
    record_attempt(fact_id, field_name, is_correct)

    # Update consecutive counters and check for demotion
    demoted = update_consecutive_attempts(fact_id, is_correct)

    # Get domain for the result page
    domain = Domain.query.get(domain_id)

    # Determine next URL based on the result
    if demoted:
        # Clear any pending review flags if this was a review question
        session.pop("pending_review_fact_id", None)
        session.pop("just_completed_fact_id", None)

        # Fact returned to unlearned - show it again with highlighted field
        mark_fact_shown(fact_id)
        next_url = url_for("show_fact", fact_id=fact_id, highlight_field=field_name)

    # If this was a review question
    elif is_review_question:
        # Clear the review flags
        session.pop("pending_review_fact_id", None)
        session.pop("just_completed_fact_id", None)

        # If wrong answer, show fact before continuing with highlighted field
        if not is_correct:
            next_url = url_for("show_fact", fact_id=fact_id, highlight_field=field_name)
        else:
            # If correct, go to next quiz question
            next_url = url_for("quiz")

    elif is_correct:
        # Check if achieved 2 consecutive correct
        if has_two_consecutive_correct(fact_id):
            # Clear pending quiz fact
            session.pop("pending_quiz_fact_id", None)

            # Set up review question
            from models import get_learned_facts
            import random

            learned_facts = get_learned_facts(domain_id)
            eligible_for_review = [f for f in learned_facts if f.id != fact_id]

            if eligible_for_review:
                # Select random fact for review
                review_fact = random.choice(eligible_for_review)
                session["pending_review_fact_id"] = review_fact.id
                session["just_completed_fact_id"] = fact_id

        # Note: question_count is now incremented in /quiz route
        # This ensures count increments on every question, not just correct answers

        # Go to next quiz question
        next_url = url_for("quiz")
    else:
        # Wrong answer - show fact again before re-quizzing with highlighted field
        next_url = url_for("show_fact", fact_id=fact_id, highlight_field=field_name)

    # Render result page with animation
    return render_template(
        "answer_result.html",
        is_correct=is_correct,
        next_url=next_url,
        domain=domain,
    )


@app.route("/reset_domain", methods=["POST"])
def reset_domain():
    """Reset all progress for current domain."""
    domain_id = session.get("domain_id")

    if domain_id:
        reset_domain_progress(domain_id)

    # Clear session
    session.clear()

    return redirect(url_for("index"))


@app.route("/reset_domain_from_menu/<int:domain_id>", methods=["POST"])
def reset_domain_from_menu(domain_id):
    """Reset progress for a specific domain from the menu."""
    reset_domain_progress(domain_id)
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    """Reset session (for testing purposes)."""
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_database()
    app.run(debug=True, host="0.0.0.0", port=5000)
