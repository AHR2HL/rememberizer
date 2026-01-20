"""Student blueprint for viewing assigned domains and progress."""

from flask import Blueprint, render_template, redirect, url_for, abort
from flask_login import current_user, login_required
from models import (
    get_user_domains,
    get_student_domain_progress,
    get_questions_answered_today,
    get_total_time_spent,
    get_unique_session_count,
    format_time_spent,
)

student_bp = Blueprint("student", __name__, url_prefix="/student")


def require_student():
    """Check if current user is a student, abort if not."""
    if not current_user.is_authenticated or current_user.role != "student":
        abort(403)


@student_bp.route("/domains")
@login_required
def domains():
    """Student domain selection - show only assigned domains with progress."""
    require_student()

    # Get assigned domains
    assigned_domains = get_user_domains(current_user.id)

    # Get progress for each domain
    domain_data = []
    for domain in assigned_domains:
        progress = get_student_domain_progress(current_user.id, domain.id)
        domain_data.append({"domain": domain, "progress": progress})

    # Get today's question count
    questions_today = get_questions_answered_today(current_user.id)

    return render_template(
        "student/domains.html", domain_data=domain_data, questions_today=questions_today
    )


@student_bp.route("/progress")
@login_required
def progress():
    """Student personal progress overview."""
    require_student()

    # Get all assigned domains with progress
    assigned_domains = get_user_domains(current_user.id)

    domain_data = []
    total_attempts = 0
    for domain in assigned_domains:
        progress = get_student_domain_progress(current_user.id, domain.id)
        domain_data.append({"domain": domain, "progress": progress})
        total_attempts += progress["attempt_count"]

    # Get engagement metrics
    questions_today = get_questions_answered_today(current_user.id)
    total_time_minutes = get_total_time_spent(current_user.id)
    session_count = get_unique_session_count(current_user.id)
    formatted_time = format_time_spent(total_time_minutes)

    return render_template(
        "student/progress.html",
        domain_data=domain_data,
        total_attempts=total_attempts,
        questions_today=questions_today,
        formatted_time=formatted_time,
        session_count=session_count,
    )
