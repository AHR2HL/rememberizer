"""Quiz and public routes blueprint for Rememberizer."""

from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import current_user
from models import Domain, Fact, FactState
from services.fact_service import (
    mark_fact_learned,
    mark_fact_shown,
    record_attempt,
    has_two_consecutive_correct,
    reset_domain_progress,
    update_consecutive_attempts,
    get_learned_facts,
    get_out_of_order_facts,
    get_attempt_count,
)
from services.domain_service import (
    is_domain_assigned,
    is_domain_visible_to_teacher,
)
from quiz_logic import (
    get_next_unlearned_fact,
    prepare_quiz_question_for_fact,
    select_next_fact,
)
import uuid
import random

quiz_bp = Blueprint("quiz", __name__)


@quiz_bp.route("/")
def index():
    """Landing page - redirect based on authentication."""
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Redirect based on role
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    elif current_user.role == "teacher":
        return redirect(url_for("teacher.dashboard"))
    else:  # student
        return redirect(url_for("student.domains"))


@quiz_bp.route("/start", methods=["POST"])
def start():
    """Initialize quiz session with selected domain."""
    from flask import flash, abort

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    domain_id = request.form.get("domain_id", type=int)

    if not domain_id:
        return redirect(url_for("quiz.index"))

    domain = Domain.query.get(domain_id)
    if not domain:
        return redirect(url_for("quiz.index"))

    # Verify domain access based on role
    if current_user.role == "student":
        # Students need domain assignment
        if not is_domain_assigned(current_user.id, domain_id):
            flash("You don't have access to this domain", "error")
            return redirect(url_for("student.domains"))
    elif current_user.role in ["teacher", "admin"]:
        # Teachers/admins need domain visibility
        if not is_domain_visible_to_teacher(domain, current_user):
            abort(403)

    # Initialize session
    session["domain_id"] = domain_id
    session["question_count"] = 0

    # Generate unique session ID for this quiz session (for engagement tracking)
    session["quiz_session_id"] = str(uuid.uuid4())

    # Initialize doom loop tracking
    session["recent_attempts"] = []
    session["consecutive_correct_in_session"] = 0
    session["doom_loop_active"] = False

    # First, check for out-of-order facts (unlearned facts before learned facts)
    # These should be re-shown before introducing new facts
    out_of_order_facts = get_out_of_order_facts(domain_id, current_user.id)

    if out_of_order_facts:
        # Re-show the first out-of-order fact
        mark_fact_shown(out_of_order_facts[0].id, current_user.id)
        return redirect(url_for("quiz.show_fact", fact_id=out_of_order_facts[0].id))

    # If no out-of-order facts, get next unlearned fact
    next_fact = get_next_unlearned_fact(domain_id, current_user.id)

    if not next_fact:
        # All facts learned, proceed to quiz
        return redirect(url_for("quiz.quiz"))

    # Show first unlearned fact (pass user_id)
    mark_fact_shown(next_fact.id, current_user.id)
    return redirect(url_for("quiz.show_fact", fact_id=next_fact.id))


def is_fact_out_of_order(fact_id, domain_id, user_id):
    """Check if a specific fact is out of order."""
    out_of_order_facts = get_out_of_order_facts(domain_id, user_id)
    return any(f.id == fact_id for f in out_of_order_facts)


@quiz_bp.route("/show_fact/<int:fact_id>")
def show_fact(fact_id):
    """Display a fact in table format."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    fact = Fact.query.get(fact_id)
    if not fact:
        return "Fact not found", 404

    domain = Domain.query.get(fact.domain_id)
    fact_data = fact.get_fact_data()
    field_names = domain.get_field_names()

    # Get highlight_field from query params (if user got question wrong)
    highlight_field = request.args.get("highlight_field", None)

    # Check if this is an out-of-order fact BEFORE marking as shown
    is_missed_learning = is_fact_out_of_order(fact_id, domain.id, current_user.id)

    # Mark as shown (but not learned yet - that happens on continue) (pass user_id)
    mark_fact_shown(fact_id, current_user.id)

    return render_template(
        "show_fact.html",
        fact=fact,
        fact_data=fact_data,
        field_names=field_names,
        domain=domain,
        highlight_field=highlight_field,
        is_missed_learning=is_missed_learning,
    )


@quiz_bp.route("/mark_learned/<int:fact_id>", methods=["POST"])
def mark_learned(fact_id):
    """Mark fact as learned when user clicks Continue."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Mark as learned (pass user_id)
    mark_fact_learned(fact_id, current_user.id)

    # Store that we need to quiz this fact next
    session["pending_quiz_fact_id"] = fact_id
    session["consecutive_correct_needed"] = 2

    return redirect(url_for("quiz.quiz"))


@quiz_bp.route("/quiz")
def quiz():
    """Generate and display next quiz question."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    domain_id = session.get("domain_id")
    question_count = session.get("question_count", 0)

    if not domain_id:
        return redirect(url_for("quiz.index"))

    # Increment question count BEFORE generating question
    # This ensures every question asked counts toward the total
    question_count += 1
    session["question_count"] = question_count

    # Check if just entered doom loop and need to start recovery
    if session.get("doom_loop_active") and not session.get(
        "doom_loop_recovery_fact_id"
    ):
        # Select recovery fact
        from doom_loop import select_recovery_fact

        # Get recent failed fact IDs to exclude
        recent = session.get("recent_attempts", [])
        excluded_ids = [a["fact_id"] for a in recent if not a["correct"]]

        recovery_fact = select_recovery_fact(domain_id, excluded_ids, current_user.id)

        if recovery_fact:
            session["doom_loop_recovery_fact_id"] = recovery_fact.id
            session["doom_loop_questions_remaining"] = 2

            # Show the fact display (like re-learning)
            mark_fact_shown(recovery_fact.id, current_user.id)
            return redirect(url_for("quiz.show_fact", fact_id=recovery_fact.id))

    # Check if we have a pending fact that needs 2 consecutive correct
    pending_fact_id = session.get("pending_quiz_fact_id")
    last_question_key = session.get("last_question_key")

    # Check if we're in review mastered mode
    review_mastered_mode = session.get("review_mastered_mode", False)

    if review_mastered_mode:
        # Select fact by least recently attempted
        from quiz_logic import select_least_recently_attempted

        fact = select_least_recently_attempted(domain_id, current_user.id)

        if fact is None:
            # Shouldn't happen, but safety check
            session.pop("review_mastered_mode", None)
            return "No facts available to review.", 200

        # Continue with normal quiz generation using this fact
        question_data = prepare_quiz_question_for_fact(
            fact, domain_id, last_question_key
        )

        # Store current question data in session
        if question_data:
            session["current_fact_id"] = question_data["fact_id"]
            session["current_field_name"] = question_data["quiz_field"]
            session["correct_index"] = question_data["correct_index"]
            session["correct_answer"] = question_data["correct_answer"]
            session["options"] = question_data["options"]
            session["context_field"] = question_data["context_field"]
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
        else:
            return "Error generating question", 400

    # Check if in doom loop recovery mode (override fact selection)
    if session.get("doom_loop_active") and session.get("doom_loop_recovery_fact_id"):
        recovery_fact_id = session["doom_loop_recovery_fact_id"]
        questions_remaining = session.get("doom_loop_questions_remaining", 0)

        if questions_remaining > 0:
            # Force quiz on recovery fact
            fact = Fact.query.get(recovery_fact_id)
            if fact:
                question_data = prepare_quiz_question_for_fact(
                    fact, domain_id, last_question_key
                )

                # Decrement counter
                session["doom_loop_questions_remaining"] = questions_remaining - 1

                # Store question data and render
                if question_data:
                    session["current_fact_id"] = question_data["fact_id"]
                    session["current_field_name"] = question_data["quiz_field"]
                    session["correct_index"] = question_data["correct_index"]
                    session["correct_answer"] = question_data["correct_answer"]
                    session["options"] = question_data["options"]
                    session["context_field"] = question_data["context_field"]
                    context_field = question_data["context_field"]
                    quiz_field = question_data["quiz_field"]
                    session["last_question_key"] = (
                        f"{fact.id}:{context_field}:{quiz_field}"
                    )

                    domain = Domain.query.get(domain_id)
                    return render_template(
                        "quiz.html",
                        question=question_data["question"],
                        options=question_data["options"],
                        domain=domain,
                    )
        else:
            # Recovery questions complete, clear recovery fact but stay in doom loop
            session.pop("doom_loop_recovery_fact_id", None)
            session.pop("doom_loop_questions_remaining", None)
            # Fall through to normal fact selection

    # Check for pending quiz fact (needs 2 consecutive correct)
    if pending_fact_id and not has_two_consecutive_correct(
        pending_fact_id, current_user.id
    ):
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
            fact = select_next_fact(domain_id, question_count, current_user.id)
            if fact is None:
                next_unlearned = get_next_unlearned_fact(domain_id, current_user.id)
                if next_unlearned:
                    mark_fact_shown(next_unlearned.id, current_user.id)
                    return redirect(
                        url_for("quiz.show_fact", fact_id=next_unlearned.id)
                    )
                else:
                    # All facts mastered - celebrate!
                    return redirect(url_for("quiz.celebrate", domain_id=domain_id))
            question_data = prepare_quiz_question_for_fact(
                fact, domain_id, last_question_key
            )

    # Normal fact selection
    else:
        # Clear pending fact if it exists
        if pending_fact_id:
            session.pop("pending_quiz_fact_id", None)

        # Select next fact
        fact = select_next_fact(domain_id, question_count, current_user.id)

        if fact is None:
            # No learned facts to quiz, show next unlearned fact
            next_unlearned = get_next_unlearned_fact(domain_id, current_user.id)
            if next_unlearned:
                mark_fact_shown(next_unlearned.id, current_user.id)
                return redirect(url_for("quiz.show_fact", fact_id=next_unlearned.id))
            else:
                # All facts mastered - celebrate!
                return redirect(url_for("quiz.celebrate", domain_id=domain_id))

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
    session["context_field"] = question_data["context_field"]
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


@quiz_bp.route("/answer", methods=["POST"])
def answer():
    """Process quiz answer and record attempt."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

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
        return redirect(url_for("quiz.index"))

    # Check if answer is correct by comparing VALUES, not indices
    # This handles the case where multiple facts have the same field value
    selected_answer = options[selected_index]
    is_correct = selected_answer == correct_answer

    # If not correct, check for "multiple correct answers" scenario
    # This happens when the question asks "Which X has Y=value?" and multiple Xs have that value
    if not is_correct:
        context_field_name = session.get("context_field")

        # Only check for multiple correct if we have context field info
        if context_field_name:
            # Get the fact being quizzed
            fact = Fact.query.get(fact_id)

            if fact:
                fact_data = fact.get_fact_data()
                context_value = fact_data.get(context_field_name)

                # Find all facts in domain
                all_facts = Fact.query.filter_by(domain_id=domain_id).all()

                # Check if selected answer matches another fact with the same context value
                for other_fact in all_facts:
                    other_data = other_fact.get_fact_data()

                    # If another fact has the same context value AND the selected answer matches its quiz field
                    if (
                        other_data.get(context_field_name) == context_value
                        and other_data.get(field_name) == selected_answer
                    ):
                        is_correct = True
                        break

    # Get session ID for engagement tracking
    quiz_session_id = session.get("quiz_session_id")

    # Record attempt (pass user_id and session_id)
    record_attempt(fact_id, field_name, is_correct, current_user.id, quiz_session_id)

    # Update streak (idempotent for same day)
    from services.streak_service import update_streak

    update_streak(current_user.id)

    # Update recent attempts (keep last 4) for doom loop detection
    recent = session.get("recent_attempts", [])
    recent.append({"fact_id": fact_id, "correct": is_correct})
    if len(recent) > 4:
        recent = recent[-4:]  # Keep only last 4
    session["recent_attempts"] = recent

    # Update consecutive correct in session for doom loop exit detection
    if is_correct:
        session["consecutive_correct_in_session"] = (
            session.get("consecutive_correct_in_session", 0) + 1
        )
    else:
        session["consecutive_correct_in_session"] = 0

    # Check for doom loop trigger (3 out of last 4 wrong)
    from doom_loop import check_doom_loop_trigger

    if not session.get("doom_loop_active") and check_doom_loop_trigger(recent):
        session["doom_loop_active"] = True
        # Recovery will start on next quiz route

    # Check if exiting doom loop (3 consecutive correct)
    if (
        session.get("doom_loop_active")
        and session.get("consecutive_correct_in_session", 0) >= 3
    ):
        session["doom_loop_active"] = False
        session.pop("doom_loop_recovery_fact_id", None)
        session.pop("doom_loop_questions_remaining", None)

    # Update consecutive counters and check for demotion (pass user_id)
    demoted = update_consecutive_attempts(fact_id, is_correct, current_user.id)

    # Get domain for the result page
    domain = Domain.query.get(domain_id)

    # Determine next URL based on the result
    if demoted:
        # Clear any pending review flags if this was a review question
        session.pop("pending_review_fact_id", None)
        session.pop("just_completed_fact_id", None)

        # Fact returned to unlearned - show it again with highlighted field
        mark_fact_shown(fact_id, current_user.id)
        next_url = url_for(
            "quiz.show_fact", fact_id=fact_id, highlight_field=field_name
        )

    # If this was a review question
    elif is_review_question:
        # Clear the review flags
        session.pop("pending_review_fact_id", None)
        session.pop("just_completed_fact_id", None)

        # If wrong answer, show fact before continuing with highlighted field
        if not is_correct:
            next_url = url_for(
                "quiz.show_fact", fact_id=fact_id, highlight_field=field_name
            )
        else:
            # If correct, go to next quiz question
            next_url = url_for("quiz.quiz")

    elif is_correct:
        # Check if achieved 2 consecutive correct (pass user_id)
        if has_two_consecutive_correct(fact_id, current_user.id):
            # Clear pending quiz fact
            session.pop("pending_quiz_fact_id", None)

            # Set up review question
            # Get learned facts (pass user_id)
            learned_facts = get_learned_facts(domain_id, current_user.id)
            eligible_for_review = [f for f in learned_facts if f.id != fact_id]

            if eligible_for_review:
                # Select random fact for review
                review_fact = random.choice(eligible_for_review)
                session["pending_review_fact_id"] = review_fact.id
                session["just_completed_fact_id"] = fact_id

        # Note: question_count is now incremented in /quiz route
        # This ensures count increments on every question, not just correct answers

        # Go to next quiz question
        next_url = url_for("quiz.quiz")
    else:
        # Wrong answer - show fact again before re-quizzing with highlighted field
        next_url = url_for(
            "quiz.show_fact", fact_id=fact_id, highlight_field=field_name
        )

    # Render result page with animation
    return render_template(
        "answer_result.html",
        is_correct=is_correct,
        next_url=next_url,
        domain=domain,
    )


@quiz_bp.route("/reset_domain", methods=["POST"])
def reset_domain():
    """Reset all progress for current domain."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    domain_id = session.get("domain_id")

    if domain_id:
        # Reset progress for current user only (pass user_id)
        reset_domain_progress(domain_id, current_user.id)

    # Clear session
    session.clear()

    return redirect(url_for("quiz.index"))


@quiz_bp.route("/reset_domain_from_menu/<int:domain_id>", methods=["POST"])
def reset_domain_from_menu(domain_id):
    """Reset progress for a specific domain from the menu."""
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Reset progress for current user only (pass user_id)
    reset_domain_progress(domain_id, current_user.id)
    return redirect(url_for("quiz.index"))


@quiz_bp.route("/reset", methods=["POST"])
def reset():
    """Reset session (for testing purposes)."""
    session.clear()
    return redirect(url_for("quiz.index"))


@quiz_bp.route("/celebrate/<int:domain_id>")
def celebrate(domain_id):
    """Display celebration screen for completing a domain."""
    from flask_login import login_required

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    domain = Domain.query.get_or_404(domain_id)

    # Get completion statistics
    from services.progress_service import (
        get_student_domain_progress,
        format_time_spent,
        get_unique_session_count,
    )

    progress = get_student_domain_progress(current_user.id, domain_id)

    # Format time for display
    time_display = format_time_spent(progress["time_spent_minutes"])

    # Get unique session count for this domain
    session_count = get_unique_session_count(current_user.id, domain_id)

    return render_template(
        "celebration.html",
        domain=domain,
        total_facts=progress["total_facts"],
        attempt_count=progress["attempt_count"],
        time_spent=time_display,
        session_count=session_count,
    )


@quiz_bp.route("/continue_mastered/<int:domain_id>")
def continue_mastered_domain(domain_id):
    """Continue quizzing a fully-mastered domain.

    Prioritizes facts that were attempted longest ago.
    """
    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # Clear any pending facts
    session.pop("pending_quiz_fact_id", None)
    session.pop("consecutive_correct_needed", None)
    session.pop("pending_review_fact_id", None)
    session.pop("doom_loop_active", None)

    # Set domain and increment question count
    session["domain_id"] = domain_id
    session["question_count"] = session.get("question_count", 0)

    # Flag that we're in "review mastered" mode
    session["review_mastered_mode"] = True

    # Redirect to quiz
    return redirect(url_for("quiz.quiz"))
