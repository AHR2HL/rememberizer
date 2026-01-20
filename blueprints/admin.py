"""Admin blueprint for managing teachers."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from models import db, User, Domain
from services.user_service import create_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def require_admin():
    """Check if current user is admin, abort if not."""
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    """Admin dashboard."""
    require_admin()

    # Get stats
    teachers = (
        User.query.filter_by(
            role="teacher", organization_id=current_user.organization_id, is_active=True
        )
        .order_by(User.last_name, User.first_name)
        .all()
    )

    teacher_count = len(teachers)
    student_count = User.query.filter_by(
        role="student", organization_id=current_user.organization_id, is_active=True
    ).count()
    domain_count = Domain.query.count()

    return render_template(
        "admin/dashboard.html",
        teachers=teachers,
        teacher_count=teacher_count,
        student_count=student_count,
        domain_count=domain_count,
    )


@admin_bp.route("/teachers/create", methods=["GET", "POST"])
@login_required
def create_teacher():
    """Create a new teacher."""
    require_admin()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        try:
            # Import here to avoid circular import
            from app import send_user_setup_notification

            # Create teacher WITHOUT password (they'll set it via token)
            teacher = create_user(
                email=email,
                password=None,  # No password - use token-based setup
                role="teacher",
                first_name=first_name,
                last_name=last_name,
                organization_id=current_user.organization_id,
                created_by_id=current_user.id,
            )

            # Send setup notification (email or display link)
            send_user_setup_notification(teacher, "Teacher")

            return redirect(url_for("admin.dashboard"))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/create_teacher.html")

    return render_template("admin/create_teacher.html")


@admin_bp.route("/teachers/<int:teacher_id>/deactivate", methods=["POST"])
@login_required
def deactivate_teacher(teacher_id):
    """Deactivate a teacher."""
    require_admin()

    teacher = User.query.get(teacher_id)

    if not teacher or teacher.role != "teacher":
        flash("Teacher not found", "error")
        return redirect(url_for("admin.dashboard"))

    # Check teacher is in same org
    if teacher.organization_id != current_user.organization_id:
        abort(403)

    teacher.is_active = False
    db.session.commit()

    flash(f"Teacher {teacher.get_full_name()} deactivated", "success")
    return redirect(url_for("admin.dashboard"))
