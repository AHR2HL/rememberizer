"""Authentication routes blueprint for Rememberizer."""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, current_user
from models import User, authenticate_user, db
from auth import AuthUser
from werkzeug.security import generate_password_hash
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


def send_setup_email(user, setup_url):
    """
    Send password setup email to a new user.

    Returns True if email sent successfully, False otherwise.
    """
    try:
        # Try to use Flask-Mail if configured
        from flask_mail import Mail, Message
        from flask import current_app

        # Check if mail is configured
        if not current_app.config.get("MAIL_SERVER"):
            return False

        mail = Mail(current_app)

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
<body style="font-family: monospace; background-color: #000; """
            f"""color: #00FF00; padding: 20px;">
    <h2>Welcome to Rememberizer</h2>
    <p>Hello {user.first_name} {user.last_name},</p>
    <p>Your Rememberizer account has been created!</p>
    <p>To complete your setup and create your password, """
            f"""please click below:</p>
    <p><a href="{setup_url}" """
            f"""style="color: #00FF00; font-weight: bold;">"""
            f"""[SET UP YOUR ACCOUNT]</a></p>
    <p>Or copy this link: {setup_url}</p>
    <p style="color: #FFFF00;">This link will expire in 7 days.</p>
    <p style="font-size: 12px; color: #00AA00;">"""
            f"""If you did not request this account, please ignore this email.</p>
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
    # Generate setup URL
    setup_url = url_for("auth.setup_password", token=user.setup_token, _external=True)

    # Try to send email (optional - fail gracefully)
    email_sent = send_setup_email(user, setup_url)

    if email_sent:
        flash(
            f"{role_name} {user.get_full_name()} created! "
            f"Setup email sent to {user.email}",
            "success",
        )
    else:
        # Email failed - show the link to the creator
        flash(f"{role_name} {user.get_full_name()} created successfully!", "success")
        flash(f"Setup link (valid 7 days): {setup_url}", "info")
        flash(f"Please share this link with the {role_name.lower()} securely.", "info")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        else:  # student
            return redirect(url_for("student.domains"))

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
                return redirect(url_for("admin.dashboard"))
            elif user.role == "teacher":
                return redirect(url_for("teacher.dashboard"))
            else:  # student
                return redirect(url_for("student.domains"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Handle user logout."""
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/setup-password/<token>", methods=["GET", "POST"])
def setup_password(token):
    """Handle first-time password setup via token."""
    # Find user by token
    user = User.query.filter_by(setup_token=token).first()

    if not user:
        flash("Invalid setup link. Please contact your administrator.", "error")
        return redirect(url_for("auth.login"))

    # Check if token expired
    if user.setup_token_expires and user.setup_token_expires < datetime.utcnow():
        flash(
            "This setup link has expired. Please contact your administrator.", "error"
        )
        return redirect(url_for("auth.login"))

    # Check if password already set
    if user.password_hash:
        flash("Your password has already been set. Please log in.", "info")
        return redirect(url_for("auth.login"))

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

        flash("Password set successfully! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("setup_password.html", user=user, token=token)
