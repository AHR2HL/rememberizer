"""Teacher blueprint for managing students and domains."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from models import db, User, Domain
from services.user_service import create_user
import json
import csv
import io

teacher_bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def require_teacher_or_admin():
    """Check if current user is teacher or admin, abort if not."""
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        abort(403)


# ============================================================================
# TEACHER DASHBOARD
# ============================================================================


@teacher_bp.route("/dashboard")
@login_required
def dashboard():
    """Teacher dashboard showing all students and their progress."""
    from services.user_service import get_students_by_teacher
    from services.domain_service import get_user_domains
    from services.progress_service import (
        get_progress_string,
        get_questions_answered_today,
        is_domain_complete,
    )
    from models import Domain, Attempt

    require_teacher_or_admin()

    # Get all students in teacher's organization
    students = get_students_by_teacher(current_user.id)

    # Get available domains for display
    domains = Domain.query.all()

    # Prepare student data with progress info
    student_data = []
    for student in students:
        # Get assigned domains
        assigned_domains = get_user_domains(student.id)

        # Get progress strings for each assigned domain
        domain_progress = []
        for domain in assigned_domains:
            progress_str = get_progress_string(domain.id, student.id)
            is_complete = is_domain_complete(student.id, domain.id)
            domain_progress.append(
                {"domain": domain, "progress": progress_str, "is_complete": is_complete}
            )

        # Get engagement metrics
        questions_today = get_questions_answered_today(student.id)
        total_questions = Attempt.query.filter_by(user_id=student.id).count()

        student_data.append(
            {
                "student": student,
                "assigned_domains": assigned_domains,
                "domain_progress": domain_progress,
                "total_domains": len(assigned_domains),
                "questions_today": questions_today,
                "total_questions": total_questions,
            }
        )

    return render_template(
        "teacher/dashboard.html", student_data=student_data, available_domains=domains
    )


# ============================================================================
# TEACHER DOMAIN MANAGEMENT ROUTES
# ============================================================================


@teacher_bp.route("/domains")
@login_required
def domains():
    """List all available domains with testing option."""
    from services.domain_service import get_visible_domains
    from services.progress_service import (
        get_student_domain_progress,
        is_domain_complete,
    )

    require_teacher_or_admin()

    # Get domains visible to this teacher
    visible_domains = get_visible_domains(current_user.id, current_user.organization_id)

    # For each domain, get teacher's progress
    domain_data = []
    for domain in visible_domains:
        progress = get_student_domain_progress(current_user.id, domain.id)
        if progress:
            progress["is_complete"] = is_domain_complete(current_user.id, domain.id)
        domain_data.append(
            {
                "domain": domain,
                "progress": progress,
                "created_by_me": domain.created_by == current_user.id,
            }
        )

    return render_template("teacher/domains.html", domain_data=domain_data)


@teacher_bp.route("/domains/create", methods=["GET"])
@login_required
def create_domain_form():
    """Display domain creation form."""
    require_teacher_or_admin()

    return render_template("teacher/create_domain.html")


@teacher_bp.route("/domains/create", methods=["POST"])
@login_required
def create_domain():
    """Process domain creation (form or CSV)."""
    require_teacher_or_admin()

    upload_method = request.form.get("upload_method")  # "form" or "csv"

    if upload_method == "csv":
        # Handle CSV upload
        if "csv_file" not in request.files:
            flash("No file uploaded", "error")
            return redirect(url_for("teacher.create_domain_form"))

        file = request.files["csv_file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("teacher.create_domain_form"))

        if not file.filename.endswith(".csv"):
            flash("File must be a CSV", "error")
            return redirect(url_for("teacher.create_domain_form"))

        domain_name = request.form.get("domain_name", "").strip()
        if not domain_name:
            flash("Domain name is required", "error")
            return redirect(url_for("teacher.create_domain_form"))

        # Parse CSV
        try:
            csv_content = file.read().decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # First row is header (field names)
            field_names = list(csv_reader.fieldnames)

            # Read all facts
            facts_data = [row for row in csv_reader]

            # Create domain
            from services.domain_service import create_custom_domain

            domain = create_custom_domain(
                name=domain_name,
                field_names=field_names,
                facts_data=facts_data,
                created_by=current_user.id,
                organization_id=current_user.organization_id,
            )

            flash(
                f"Domain '{domain.name}' created from CSV with "
                f"{len(facts_data)} facts!",
                "success",
            )
            return redirect(url_for("teacher.domains"))

        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("teacher.create_domain_form"))
        except Exception as e:
            flash(f"Error processing CSV: {str(e)}", "error")
            return redirect(url_for("teacher.create_domain_form"))

    else:
        # Handle form creation
        domain_name = request.form.get("domain_name", "").strip()
        field_names_raw = request.form.get("field_names", "").strip()
        facts_json = request.form.get("facts_json", "").strip()

        # Validate inputs
        if not domain_name or not field_names_raw or not facts_json:
            flash("All fields are required", "error")
            return redirect(url_for("teacher.create_domain_form"))

        # Parse field names (comma-separated)
        field_names = [f.strip() for f in field_names_raw.split(",")]

        # Parse facts (JSON array)
        try:
            facts_data = json.loads(facts_json)
        except json.JSONDecodeError:
            flash("Invalid JSON format for facts", "error")
            return redirect(url_for("teacher.create_domain_form"))

        # Validate facts structure
        for fact in facts_data:
            if not all(field in fact for field in field_names):
                flash(
                    f"Each fact must have all fields: {', '.join(field_names)}", "error"
                )
                return redirect(url_for("teacher.create_domain_form"))

        # Create domain and facts
        try:
            from services.domain_service import create_custom_domain

            domain = create_custom_domain(
                name=domain_name,
                field_names=field_names,
                facts_data=facts_data,
                created_by=current_user.id,
                organization_id=current_user.organization_id,
            )

            flash(f"Domain '{domain.name}' created successfully!", "success")
            return redirect(url_for("teacher.domains"))

        except ValueError as e:
            flash(f"Validation error: {str(e)}", "error")
            return redirect(url_for("teacher.create_domain_form"))


@teacher_bp.route("/domains/<int:domain_id>/publish", methods=["POST"])
@login_required
def toggle_publish_domain(domain_id):
    """Publish or unpublish a domain (creator only)."""
    from services.domain_service import update_domain_published_status

    require_teacher_or_admin()

    domain = Domain.query.get_or_404(domain_id)

    # Verify creator (or admin)
    if domain.created_by != current_user.id and current_user.role != "admin":
        abort(403)

    # Toggle published status
    action = request.form.get("action")  # "publish" or "unpublish"
    is_published = action == "publish"

    update_domain_published_status(domain_id, is_published)

    status = "published" if is_published else "unpublished"
    flash(f"Domain '{domain.name}' {status} successfully!", "success")
    return redirect(url_for("teacher.domains"))


# ============================================================================
# END TEACHER DOMAIN MANAGEMENT ROUTES
# ============================================================================


# ============================================================================
# TEACHER STUDENT MANAGEMENT ROUTES
# ============================================================================


@teacher_bp.route("/students/create", methods=["GET", "POST"])
@login_required
def create_student():
    """Create a new student."""
    require_teacher_or_admin()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        try:
            # Import here to avoid circular import
            from app import send_user_setup_notification

            # Create student WITHOUT password (they'll set it via token)
            student = create_user(
                email=email,
                password=None,  # No password - use token-based setup
                role="student",
                first_name=first_name,
                last_name=last_name,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id,
            )

            # Send setup notification (email or display link)
            send_user_setup_notification(student, "Student")

            return redirect(url_for("teacher.dashboard"))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("teacher/create_student.html")

    return render_template("teacher/create_student.html")


@teacher_bp.route("/students/<int:student_id>")
@login_required
def student_detail(student_id):
    """View detailed student progress."""
    from services.domain_service import get_user_domains
    from services.progress_service import (
        get_student_domain_progress,
        get_questions_answered_today,
        get_total_time_spent,
        get_unique_session_count,
        format_time_spent,
        is_domain_complete,
    )
    from services.streak_service import get_streak_info
    from models import User, Domain, Attempt

    require_teacher_or_admin()

    student = User.query.get(student_id)

    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher.dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        abort(403)

    # Get assigned domains with detailed progress
    assigned_domains = get_user_domains(student.id)
    all_domains = Domain.query.all()

    domain_details = []
    for domain in all_domains:
        is_assigned = any(d.id == domain.id for d in assigned_domains)

        if is_assigned:
            progress_data = get_student_domain_progress(student.id, domain.id)
            if progress_data:
                progress_data["is_complete"] = is_domain_complete(student.id, domain.id)
            domain_details.append(
                {"domain": domain, "is_assigned": True, "progress": progress_data}
            )
        else:
            domain_details.append(
                {"domain": domain, "is_assigned": False, "progress": None}
            )

    # Get engagement metrics
    questions_today = get_questions_answered_today(student.id)
    total_time_minutes = get_total_time_spent(student.id)
    session_count = get_unique_session_count(student.id)
    formatted_time = format_time_spent(total_time_minutes)
    total_questions = Attempt.query.filter_by(user_id=student.id).count()

    # Get streak info for this student
    streak_info = get_streak_info(student.id)

    return render_template(
        "teacher/student_detail.html",
        student=student,
        domain_details=domain_details,
        questions_today=questions_today,
        formatted_time=formatted_time,
        session_count=session_count,
        total_questions=total_questions,
        streak_info=streak_info,
    )


@teacher_bp.route("/students/<int:student_id>/assign", methods=["POST"])
@login_required
def assign_domain_to_student(student_id):
    """Assign a domain to a student."""
    from services.domain_service import assign_domain_to_user
    from models import User

    require_teacher_or_admin()

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher.dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        abort(403)

    domain_id = request.form.get("domain_id", type=int)
    if not domain_id:
        flash("No domain selected", "error")
        return redirect(url_for("teacher.student_detail", student_id=student_id))

    try:
        assign_domain_to_user(student.id, domain_id, current_user.id)
        from models import Domain

        domain = Domain.query.get(domain_id)
        flash(f"Assigned {domain.name} to {student.get_full_name()}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("teacher.student_detail", student_id=student_id))


@teacher_bp.route("/students/<int:student_id>/unassign", methods=["POST"])
@login_required
def unassign_domain_from_student(student_id):
    """Unassign a domain from a student."""
    from services.domain_service import unassign_domain_from_user
    from models import User

    require_teacher_or_admin()

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher.dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        abort(403)

    domain_id = request.form.get("domain_id", type=int)
    if not domain_id:
        flash("No domain selected", "error")
        return redirect(url_for("teacher.student_detail", student_id=student_id))

    try:
        unassign_domain_from_user(student.id, domain_id)
        from models import Domain

        domain = Domain.query.get(domain_id)
        flash(f"Unassigned {domain.name} from {student.get_full_name()}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("teacher.student_detail", student_id=student_id))


@teacher_bp.route(
    "/students/<int:student_id>/reset-domain/<int:domain_id>", methods=["POST"]
)
@login_required
def reset_student_domain_progress(student_id, domain_id):
    """Reset a student's progress for a specific domain."""
    from services.fact_service import reset_domain_progress
    from models import User, Domain

    require_teacher_or_admin()

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher.dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        abort(403)

    domain = Domain.query.get(domain_id)
    if not domain:
        flash("Domain not found", "error")
        return redirect(url_for("teacher.student_detail", student_id=student_id))

    # Reset progress for this student only
    reset_domain_progress(domain_id, student.id)
    flash(f"Reset {student.get_full_name()}'s progress for {domain.name}", "success")

    return redirect(url_for("teacher.student_detail", student_id=student_id))


@teacher_bp.route("/students/<int:student_id>/deactivate", methods=["POST"])
@login_required
def deactivate_student(student_id):
    """Deactivate a student."""
    require_teacher_or_admin()

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher.dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        abort(403)

    student.is_active = False
    db.session.commit()

    flash(f"Student {student.get_full_name()} deactivated", "success")
    return redirect(url_for("teacher.dashboard"))


# ============================================================================
# END TEACHER STUDENT MANAGEMENT ROUTES
# ============================================================================
