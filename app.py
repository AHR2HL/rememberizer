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

    # Mark as shown (but not learned yet - that happens on continue)
    mark_fact_shown(fact_id)

    return render_template(
        "show_fact.html",
        fact=fact,
        fact_data=fact_data,
        field_names=field_names,
        domain=domain,
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

    if pending_fact_id and not has_two_consecutive_correct(pending_fact_id):
        # Continue quizzing this fact until 2 consecutive correct
        fact = Fact.query.get(pending_fact_id)
        question_data = prepare_quiz_question_for_fact(fact, domain_id, last_question_key)
    else:
        # Clear pending fact
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

        question_data = prepare_quiz_question_for_fact(fact, domain_id, last_question_key)

    if not question_data:
        return "Error generating question", 400

    # Store current question data in session
    session["current_fact_id"] = question_data["fact_id"]
    session["current_field_name"] = question_data["quiz_field"]
    session["correct_index"] = question_data["correct_index"]
    session["last_question_key"] = f"{question_data['fact_id']}:{question_data['context_field']}:{question_data['quiz_field']}"

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
    correct_index = session.get("correct_index")
    question_count = session.get("question_count", 0)

    if fact_id is None or field_name is None or correct_index is None:
        return redirect(url_for("index"))

    # Check if answer is correct
    is_correct = selected_index == correct_index

    # Record attempt
    record_attempt(fact_id, field_name, is_correct)

    # Update consecutive counters and check for demotion
    demoted = update_consecutive_attempts(fact_id, is_correct)

    if demoted:
        # Fact returned to unlearned - show it again
        mark_fact_shown(fact_id)
        return redirect(url_for("show_fact", fact_id=fact_id))

    if is_correct:
        # Check if achieved 2 consecutive correct
        if has_two_consecutive_correct(fact_id):
            # Clear pending quiz fact
            session.pop("pending_quiz_fact_id", None)

        # Note: question_count is now incremented in /quiz route
        # This ensures count increments on every question, not just correct answers

        # Go to next quiz question
        return redirect(url_for("quiz"))
    else:
        # Wrong answer - show fact again before re-quizzing
        return redirect(url_for("show_fact", fact_id=fact_id))


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
