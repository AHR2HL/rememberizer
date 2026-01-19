"""Main Flask application for Rememberizer quiz app."""

import os
from flask import Flask, render_template, request, redirect, url_for, session
from models import (
    db,
    Domain,
    Fact,
    User,
    Organization,
    UserDomainAssignment,
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

# Initialize Flask-Login
from auth import login_manager

login_manager.init_app(app)

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
    """Generate progress string for a domain for the current user."""
    from models import get_progress_string
    from flask_login import current_user

    # If user is not authenticated, return empty string
    if not current_user.is_authenticated:
        return ""

    return get_progress_string(domain_id, current_user.id)


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
        # Create all tables if they don't exist
        db.create_all()

        # Load all JSON files from facts directory
        load_all_domains_from_directory("facts")

        # Check if admin account exists
        from models import create_user

        admin = User.query.filter_by(role="admin").first()

        if not admin:
            # Ensure default organization exists
            org = Organization.query.get(1)
            if not org:
                org = Organization(id=1, name="Default Organization")
                db.session.add(org)
                db.session.commit()

            print("\n" + "=" * 60)
            print("FIRST-TIME SETUP: ADMIN ACCOUNT CREATION")
            print("=" * 60)
            print("\nNo admin account found. You need to create one to manage")
            print("teachers and students in the Rememberizer system.")
            print("\nThe admin email will be: admin@admin.admin")

            response = input("\nCreate admin account now? [Y/n]: ").strip().lower()

            if response in ["", "y", "yes"]:
                while True:
                    password = input("Enter admin password (min 8 chars): ").strip()

                    if len(password) < 8:
                        print(
                            "[ERROR] Password must be at least 8 characters long. Try again."
                        )
                        continue

                    # Confirm password
                    confirm = input("Confirm admin password: ").strip()

                    if password != confirm:
                        print("[ERROR] Passwords do not match. Try again.\n")
                        continue

                    # Create admin user
                    try:
                        admin = create_user(
                            email="admin@admin.admin",
                            password=password,
                            role="admin",
                            first_name="Admin",
                            last_name="User",
                            organization_id=1,
                        )

                        print("\n" + "=" * 60)
                        print("[OK] Admin account created successfully!")
                        print("=" * 60)
                        print("\nLogin credentials:")
                        print(f"  Email:    admin@admin.admin")
                        print(f"  Password: (the password you just set)")
                        print("\nYou can now start the application and log in.")
                        print("=" * 60 + "\n")
                        break

                    except ValueError as e:
                        print(f"[ERROR] Error creating admin: {e}")
                        break
            else:
                print("\nAdmin account creation skipped.")
                print("You can create one later by running the application again.")
                print("=" * 60 + "\n")

        _db_initialized = True


@app.before_request
def ensure_database():
    """Ensure database is initialized before first request."""
    init_database()


@app.before_request
def update_last_active():
    """Update last_active timestamp for authenticated users."""
    from flask_login import current_user
    from datetime import datetime

    if current_user.is_authenticated:
        # Update last_active timestamp
        current_user._user.last_active = datetime.utcnow()
        db.session.commit()


def send_setup_email(user, setup_url):
    """
    Send password setup email to a new user.

    Returns True if email sent successfully, False otherwise.
    """
    try:
        # Try to use Flask-Mail if configured
        from flask_mail import Mail, Message

        # Check if mail is configured
        if not app.config.get("MAIL_SERVER"):
            return False

        mail = Mail(app)

        msg = Message(
            subject="Welcome to Rememberizer - Set Your Password",
            recipients=[user.email],
            body=f"""
Hello {user.first_name} {user.last_name},

Your Rememberizer account has been created!

To complete your setup and create your password, please visit:
{setup_url}

This link will expire in 7 days.

If you did not request this account, please ignore this email.

Best regards,
The Rememberizer Team
            """,
            html=f"""
<html>
<body style="font-family: monospace; background-color: #000; color: #00FF00; padding: 20px;">
    <h2>Welcome to Rememberizer</h2>
    <p>Hello {user.first_name} {user.last_name},</p>
    <p>Your Rememberizer account has been created!</p>
    <p>To complete your setup and create your password, please click below:</p>
    <p><a href="{setup_url}" style="color: #00FF00; font-weight: bold;">[SET UP YOUR ACCOUNT]</a></p>
    <p>Or copy this link: {setup_url}</p>
    <p style="color: #FFFF00;">This link will expire in 7 days.</p>
    <p style="font-size: 12px; color: #00AA00;">If you did not request this account, please ignore this email.</p>
</body>
</html>
            """,
        )

        mail.send(msg)
        return True

    except Exception as e:
        # Email sending failed - that's okay, we'll show the link instead
        print(f"Email sending failed: {e}")
        return False


def send_user_setup_notification(user, role_name):
    """
    Handle token-based setup notification for a new user.

    Generates setup URL, attempts to send email, and displays appropriate
    flash messages based on success/failure.

    Args:
        user: The newly created User object (must have setup_token)
        role_name: Display name for the user role (e.g., "Teacher", "Student")

    Returns:
        None (displays flash messages directly)
    """
    from flask import flash

    # Generate setup URL
    setup_url = url_for("setup_password", token=user.setup_token, _external=True)

    # Try to send email (optional - fail gracefully)
    email_sent = send_setup_email(user, setup_url)

    if email_sent:
        flash(
            f"{role_name} {user.get_full_name()} created! Setup email sent to {user.email}",
            "success",
        )
    else:
        # Email failed - show the link to the creator
        flash(f"{role_name} {user.get_full_name()} created successfully!", "success")
        flash(f"Setup link (valid 7 days): {setup_url}", "info")
        flash(f"Please share this link with the {role_name.lower()} securely.", "info")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    from flask_login import login_user, current_user
    from models import authenticate_user
    from auth import AuthUser

    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif current_user.role == "teacher":
            return redirect(url_for("teacher_dashboard"))
        else:  # student
            return redirect(url_for("student_domains"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = authenticate_user(email, password)

        if user:
            # Wrap in AuthUser and log in
            auth_user = AuthUser(user)
            login_user(auth_user)

            # Redirect based on role
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "teacher":
                return redirect(url_for("teacher_dashboard"))
            else:  # student
                return redirect(url_for("student_domains"))
        else:
            from flask import flash

            flash("Invalid email or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Handle user logout."""
    from flask_login import logout_user

    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.route("/setup-password/<token>", methods=["GET", "POST"])
def setup_password(token):
    """Handle first-time password setup via token."""
    from models import User
    from werkzeug.security import generate_password_hash
    from flask import flash
    from datetime import datetime

    # Find user by token
    user = User.query.filter_by(setup_token=token).first()

    if not user:
        flash("Invalid setup link. Please contact your administrator.", "error")
        return redirect(url_for("login"))

    # Check if token expired
    if user.setup_token_expires and user.setup_token_expires < datetime.utcnow():
        flash(
            "This setup link has expired. Please contact your administrator.", "error"
        )
        return redirect(url_for("login"))

    # Check if password already set
    if user.password_hash:
        flash("Your password has already been set. Please log in.", "info")
        return redirect(url_for("login"))

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validate passwords match
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("setup_password.html", user=user, token=token)

        # Validate password length
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template("setup_password.html", user=user, token=token)

        # Set password
        user.password_hash = generate_password_hash(password, method="scrypt")
        user.setup_token = None  # Clear token
        user.setup_token_expires = None
        db.session.commit()

        flash(f"Password set successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("setup_password.html", user=user, token=token)


# ============================================================================
# ADMIN ROUTES
# ============================================================================


@app.route("/admin/dashboard")
def admin_dashboard():
    """Admin dashboard."""
    from auth import role_required
    from models import User, Domain
    from flask_login import current_user

    # Check if user is admin
    if not current_user.is_authenticated or current_user.role != "admin":
        from flask import abort

        abort(403)

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


@app.route("/admin/teachers/create", methods=["GET", "POST"])
def create_teacher():
    """Create a new teacher."""
    from flask_login import current_user
    from models import create_user
    from flask import flash

    # Check if user is admin
    if not current_user.is_authenticated or current_user.role != "admin":
        from flask import abort

        abort(403)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        try:
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

            return redirect(url_for("admin_dashboard"))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/create_teacher.html")

    return render_template("admin/create_teacher.html")


@app.route("/admin/teachers/<int:teacher_id>/deactivate", methods=["POST"])
def deactivate_teacher(teacher_id):
    """Deactivate a teacher."""
    from flask_login import current_user
    from models import User
    from flask import flash

    # Check if user is admin
    if not current_user.is_authenticated or current_user.role != "admin":
        from flask import abort

        abort(403)

    teacher = User.query.get(teacher_id)

    if not teacher or teacher.role != "teacher":
        flash("Teacher not found", "error")
        return redirect(url_for("admin_dashboard"))

    # Check teacher is in same org
    if teacher.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    teacher.is_active = False
    db.session.commit()

    flash(f"Teacher {teacher.get_full_name()} deactivated", "success")
    return redirect(url_for("admin_dashboard"))


# ============================================================================
# TEACHER ROUTES
# ============================================================================


@app.route("/teacher/dashboard")
def teacher_dashboard():
    """Teacher dashboard showing all students and their progress."""
    from flask_login import current_user
    from models import (
        get_students_by_teacher,
        get_user_domains,
        get_progress_string,
        Domain,
        get_questions_answered_today,
        Attempt,
    )

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    # Get all students in teacher's organization
    from models import get_students_by_teacher

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
            domain_progress.append({"domain": domain, "progress": progress_str})

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


@app.route("/teacher/students/create", methods=["GET", "POST"])
def create_student():
    """Create a new student."""
    from flask_login import current_user
    from models import create_user
    from flask import flash

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        try:
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

            return redirect(url_for("teacher_dashboard"))

        except ValueError as e:
            flash(str(e), "error")
            return render_template("teacher/create_student.html")

    return render_template("teacher/create_student.html")


@app.route("/teacher/students/<int:student_id>")
def student_detail(student_id):
    """View detailed student progress."""
    from flask_login import current_user
    from models import (
        User,
        get_user_domains,
        get_student_domain_progress,
        Domain,
        get_questions_answered_today,
        get_total_time_spent,
        get_unique_session_count,
        format_time_spent,
        Attempt,
    )

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    student = User.query.get(student_id)

    if not student or student.role != "student":
        from flask import flash

        flash("Student not found", "error")
        return redirect(url_for("teacher_dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    # Get assigned domains with detailed progress
    assigned_domains = get_user_domains(student.id)
    all_domains = Domain.query.all()

    domain_details = []
    for domain in all_domains:
        is_assigned = any(d.id == domain.id for d in assigned_domains)

        if is_assigned:
            progress_data = get_student_domain_progress(student.id, domain.id)
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

    return render_template(
        "teacher/student_detail.html",
        student=student,
        domain_details=domain_details,
        questions_today=questions_today,
        formatted_time=formatted_time,
        session_count=session_count,
        total_questions=total_questions,
    )


@app.route("/teacher/students/<int:student_id>/assign", methods=["POST"])
def assign_domain_to_student(student_id):
    """Assign a domain to a student."""
    from flask_login import current_user
    from models import User, assign_domain_to_user
    from flask import flash

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher_dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    domain_id = request.form.get("domain_id", type=int)
    if not domain_id:
        flash("No domain selected", "error")
        return redirect(url_for("student_detail", student_id=student_id))

    try:
        assign_domain_to_user(student.id, domain_id, current_user.id)
        from models import Domain

        domain = Domain.query.get(domain_id)
        flash(f"Assigned {domain.name} to {student.get_full_name()}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("student_detail", student_id=student_id))


@app.route("/teacher/students/<int:student_id>/unassign", methods=["POST"])
def unassign_domain_from_student(student_id):
    """Unassign a domain from a student."""
    from flask_login import current_user
    from models import User, unassign_domain_from_user
    from flask import flash

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher_dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    domain_id = request.form.get("domain_id", type=int)
    if not domain_id:
        flash("No domain selected", "error")
        return redirect(url_for("student_detail", student_id=student_id))

    try:
        unassign_domain_from_user(student.id, domain_id)
        from models import Domain

        domain = Domain.query.get(domain_id)
        flash(f"Unassigned {domain.name} from {student.get_full_name()}", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("student_detail", student_id=student_id))


@app.route(
    "/teacher/students/<int:student_id>/reset-domain/<int:domain_id>", methods=["POST"]
)
def reset_student_domain_progress(student_id, domain_id):
    """Reset a student's progress for a specific domain."""
    from flask_login import current_user
    from models import User, reset_domain_progress, Domain
    from flask import flash

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher_dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    domain = Domain.query.get(domain_id)
    if not domain:
        flash("Domain not found", "error")
        return redirect(url_for("student_detail", student_id=student_id))

    # Reset progress for this student only
    reset_domain_progress(domain_id, student.id)
    flash(f"Reset {student.get_full_name()}'s progress for {domain.name}", "success")

    return redirect(url_for("student_detail", student_id=student_id))


@app.route("/teacher/students/<int:student_id>/deactivate", methods=["POST"])
def deactivate_student(student_id):
    """Deactivate a student."""
    from flask_login import current_user
    from models import User
    from flask import flash

    # Check if user is teacher or admin
    if not current_user.is_authenticated or current_user.role not in [
        "teacher",
        "admin",
    ]:
        from flask import abort

        abort(403)

    student = User.query.get(student_id)
    if not student or student.role != "student":
        flash("Student not found", "error")
        return redirect(url_for("teacher_dashboard"))

    # Check student is in same org
    if student.organization_id != current_user.organization_id:
        from flask import abort

        abort(403)

    student.is_active = False
    db.session.commit()

    flash(f"Student {student.get_full_name()} deactivated", "success")
    return redirect(url_for("teacher_dashboard"))


# ============================================================================
# STUDENT ROUTES
# ============================================================================


@app.route("/student/domains")
def student_domains():
    """Student domain selection - show only assigned domains with progress."""
    from flask_login import current_user, login_required
    from models import (
        get_user_domains,
        get_student_domain_progress,
        get_questions_answered_today,
    )

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    # Only students can access this
    if current_user.role != "student":
        from flask import abort

        abort(403)

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


@app.route("/student/progress")
def student_progress():
    """Student personal progress overview."""
    from flask_login import current_user
    from models import (
        get_user_domains,
        get_student_domain_progress,
        get_questions_answered_today,
        get_total_time_spent,
        get_unique_session_count,
        format_time_spent,
    )

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    # Only students can access this
    if current_user.role != "student":
        from flask import abort

        abort(403)

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


@app.route("/")
def index():
    """Landing page - redirect based on authentication."""
    from flask_login import current_user

    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    # Redirect based on role
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif current_user.role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    else:  # student
        return redirect(url_for("student_domains"))


@app.route("/start", methods=["POST"])
def start():
    """Initialize quiz session with selected domain."""
    from flask_login import current_user
    from models import is_domain_assigned
    from flask import flash

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    domain_id = request.form.get("domain_id", type=int)

    if not domain_id:
        return redirect(url_for("index"))

    domain = Domain.query.get(domain_id)
    if not domain:
        return redirect(url_for("index"))

    # Verify domain assignment for students
    if current_user.role == "student":
        if not is_domain_assigned(current_user.id, domain_id):
            flash("You don't have access to this domain", "error")
            return redirect(url_for("student_domains"))

    # Initialize session
    session["domain_id"] = domain_id
    session["question_count"] = 0

    # Generate unique session ID for this quiz session (for engagement tracking)
    import uuid

    session["quiz_session_id"] = str(uuid.uuid4())

    # Initialize doom loop tracking
    session["recent_attempts"] = []
    session["consecutive_correct_in_session"] = 0
    session["doom_loop_active"] = False

    # Get first unlearned fact to show (pass user_id)
    next_fact = get_next_unlearned_fact(domain_id, current_user.id)
    if not next_fact:
        # No unlearned facts, start quizzing
        return redirect(url_for("quiz"))

    # Show first unlearned fact (pass user_id)
    mark_fact_shown(next_fact.id, current_user.id)
    return redirect(url_for("show_fact", fact_id=next_fact.id))


@app.route("/show_fact/<int:fact_id>")
def show_fact(fact_id):
    """Display a fact in table format."""
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    fact = Fact.query.get(fact_id)
    if not fact:
        return "Fact not found", 404

    domain = Domain.query.get(fact.domain_id)
    fact_data = fact.get_fact_data()
    field_names = domain.get_field_names()

    # Get highlight_field from query params (if user got question wrong)
    highlight_field = request.args.get("highlight_field", None)

    # Mark as shown (but not learned yet - that happens on continue) (pass user_id)
    mark_fact_shown(fact_id, current_user.id)

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
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    # Mark as learned (pass user_id)
    mark_fact_learned(fact_id, current_user.id)

    # Store that we need to quiz this fact next
    session["pending_quiz_fact_id"] = fact_id
    session["consecutive_correct_needed"] = 2

    return redirect(url_for("quiz"))


@app.route("/quiz")
def quiz():
    """Generate and display next quiz question."""
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    domain_id = session.get("domain_id")
    question_count = session.get("question_count", 0)

    if not domain_id:
        return redirect(url_for("index"))

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
            return redirect(url_for("show_fact", fact_id=recovery_fact.id))

    # Check if we have a pending fact that needs 2 consecutive correct
    pending_fact_id = session.get("pending_quiz_fact_id")
    last_question_key = session.get("last_question_key")

    # Check if in doom loop recovery mode (override fact selection)
    if session.get("doom_loop_active") and session.get("doom_loop_recovery_fact_id"):
        recovery_fact_id = session["doom_loop_recovery_fact_id"]
        questions_remaining = session.get("doom_loop_questions_remaining", 0)

        if questions_remaining > 0:
            # Force quiz on recovery fact
            fact = Fact.query.get(recovery_fact_id)
            if fact:
                question_data = prepare_quiz_question_for_fact(
                    fact, domain_id, last_question_key, current_user.id
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
            fact, domain_id, last_question_key, current_user.id
        )

    # Check for pending review fact
    elif session.get("pending_review_fact_id"):
        review_fact_id = session.get("pending_review_fact_id")
        fact = Fact.query.get(review_fact_id)

        if fact:
            question_data = prepare_quiz_question_for_fact(
                fact, domain_id, last_question_key, current_user.id
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
                    return redirect(url_for("show_fact", fact_id=next_unlearned.id))
                else:
                    return "All facts mastered! Great job!", 200
            question_data = prepare_quiz_question_for_fact(
                fact, domain_id, last_question_key, current_user.id
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
                return redirect(url_for("show_fact", fact_id=next_unlearned.id))
            else:
                return "All facts mastered! Great job!", 200

        question_data = prepare_quiz_question_for_fact(
            fact, domain_id, last_question_key, current_user.id
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
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

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

    # Get session ID for engagement tracking
    quiz_session_id = session.get("quiz_session_id")

    # Record attempt (pass user_id and session_id)
    record_attempt(fact_id, field_name, is_correct, current_user.id, quiz_session_id)

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

        # Fact returned to unlearned - show it again with highlighted field (pass user_id)
        mark_fact_shown(fact_id, current_user.id)
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
        # Check if achieved 2 consecutive correct (pass user_id)
        if has_two_consecutive_correct(fact_id, current_user.id):
            # Clear pending quiz fact
            session.pop("pending_quiz_fact_id", None)

            # Set up review question
            from models import get_learned_facts
            import random

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
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    domain_id = session.get("domain_id")

    if domain_id:
        # Reset progress for current user only (pass user_id)
        reset_domain_progress(domain_id, current_user.id)

    # Clear session
    session.clear()

    return redirect(url_for("index"))


@app.route("/reset_domain_from_menu/<int:domain_id>", methods=["POST"])
def reset_domain_from_menu(domain_id):
    """Reset progress for a specific domain from the menu."""
    from flask_login import current_user

    # Require authentication
    if not current_user.is_authenticated:
        return redirect(url_for("login"))

    # Reset progress for current user only (pass user_id)
    reset_domain_progress(domain_id, current_user.id)
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset():
    """Reset session (for testing purposes)."""
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_database()
    app.run(debug=True, host="0.0.0.0", port=5000)
