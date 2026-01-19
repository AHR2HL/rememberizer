"""Database models for the Rememberizer quiz app."""

import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Domain(db.Model):
    """Represents a fact domain (e.g., Greek Muses)."""

    __tablename__ = "domains"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    filename = db.Column(db.String(200), nullable=False)
    field_names = db.Column(db.Text, nullable=False)  # JSON list of field names

    facts = db.relationship(
        "Fact", back_populates="domain", cascade="all, delete-orphan"
    )

    def get_field_names(self):
        """Parse and return field names as a list."""
        return json.loads(self.field_names)

    def set_field_names(self, fields):
        """Store field names as JSON."""
        self.field_names = json.dumps(fields)


class Organization(db.Model):
    """Represents an organization (school, institution, etc.)."""

    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    users = db.relationship("User", back_populates="organization")


class User(db.Model):
    """Represents a user (admin, teacher, or student)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(
        db.String(255), nullable=True
    )  # Nullable for new accounts
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'teacher', 'student'
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    setup_token = db.Column(
        db.String(100), nullable=True
    )  # For first-time password setup
    setup_token_expires = db.Column(db.DateTime, nullable=True)  # Token expiration

    organization = db.relationship("Organization", back_populates="users")
    domain_assignments = db.relationship(
        "UserDomainAssignment",
        foreign_keys="UserDomainAssignment.user_id",
        back_populates="user",
    )

    def get_full_name(self):
        """Return full name of user."""
        return f"{self.first_name} {self.last_name}"


class UserDomainAssignment(db.Model):
    """Represents assignment of a domain to a user (student)."""

    __tablename__ = "user_domain_assignments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey("domains.id"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "domain_id", name="uq_user_domain"),
    )

    user = db.relationship(
        "User", foreign_keys=[user_id], back_populates="domain_assignments"
    )
    domain = db.relationship("Domain")
    assigner = db.relationship("User", foreign_keys=[assigned_by])


class Fact(db.Model):
    """Represents a single fact within a domain."""

    __tablename__ = "facts"

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("domains.id"), nullable=False)
    fact_data = db.Column(db.Text, nullable=False)  # JSON object with all fields

    domain = db.relationship("Domain", back_populates="facts")
    attempts = db.relationship(
        "Attempt", back_populates="fact", cascade="all, delete-orphan"
    )

    def get_fact_data(self):
        """Parse and return fact data as a dict."""
        return json.loads(self.fact_data)

    def set_fact_data(self, data):
        """Store fact data as JSON."""
        self.fact_data = json.dumps(data)


class Attempt(db.Model):
    """Represents a quiz attempt on a specific fact field."""

    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    fact_id = db.Column(db.Integer, db.ForeignKey("facts.id"), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(50), nullable=True)

    fact = db.relationship("Fact", back_populates="attempts")
    user = db.relationship("User")


class FactState(db.Model):
    """Track learning state of facts."""

    __tablename__ = "fact_states"

    id = db.Column(db.Integer, primary_key=True)
    fact_id = db.Column(db.Integer, db.ForeignKey("facts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    learned_at = db.Column(db.DateTime, nullable=True)  # NULL = unlearned
    last_shown_at = db.Column(db.DateTime, nullable=True)
    consecutive_correct = db.Column(db.Integer, default=0)
    consecutive_wrong = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("fact_id", "user_id", name="uq_fact_user_state"),
    )

    fact = db.relationship("Fact", backref="state")
    user = db.relationship("User")


def get_mastery_status(fact_id, user_id):
    """
    Check if a fact is mastered for a specific user.

    Mastery = 6 of last 7 attempts correct AND most recent attempt correct.

    Args:
        fact_id: ID of the fact to check
        user_id: ID of the user

    Returns:
        bool: True if fact is mastered, False otherwise
    """
    # Get last 7 attempts for this fact by this user, ordered by timestamp descending
    attempts = (
        Attempt.query.filter_by(fact_id=fact_id, user_id=user_id)
        .order_by(Attempt.timestamp.desc())
        .limit(7)
        .all()
    )

    # Need at least 7 attempts to be mastered
    if len(attempts) < 7:
        return False

    # Most recent attempt must be correct
    if not attempts[0].correct:
        return False

    # Count correct attempts in last 7
    correct_count = sum(1 for attempt in attempts if attempt.correct)

    # Need at least 6 correct
    return correct_count >= 6


def get_mastered_facts(domain_id, user_id):
    """
    Get all mastered facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are mastered
    """
    # Get all facts in domain
    facts = Fact.query.filter_by(domain_id=domain_id).all()

    # Filter to only mastered facts
    mastered = [fact for fact in facts if get_mastery_status(fact.id, user_id)]

    return mastered


def record_attempt(fact_id, field_name, correct, user_id, session_id=None):
    """
    Record a quiz attempt.

    Args:
        fact_id: ID of the fact that was quizzed
        field_name: Name of the field that was quizzed
        correct: Boolean indicating if answer was correct
        user_id: ID of the user
        session_id: Optional session ID for engagement tracking

    Returns:
        Attempt: The created Attempt object
    """
    attempt = Attempt(
        fact_id=fact_id,
        field_name=field_name,
        correct=correct,
        user_id=user_id,
        session_id=session_id,
    )
    db.session.add(attempt)
    db.session.commit()
    return attempt


def get_unmastered_facts(domain_id, user_id):
    """
    Get all unmastered facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unmastered = [fact for fact in facts if not get_mastery_status(fact.id, user_id)]
    return unmastered


def get_attempt_count(fact_id, user_id):
    """
    Get the total number of attempts for a fact by a specific user.

    Args:
        fact_id: ID of the fact
        user_id: ID of the user

    Returns:
        int: Number of attempts
    """
    return Attempt.query.filter_by(fact_id=fact_id, user_id=user_id).count()


def mark_fact_learned(fact_id, user_id):
    """
    Mark fact as learned when user views it and clicks Continue.

    Args:
        fact_id: ID of the fact to mark as learned
        user_id: ID of the user

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(fact_id=fact_id, user_id=user_id)
        db.session.add(state)
    state.learned_at = datetime.utcnow()
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def mark_fact_shown(fact_id, user_id):
    """
    Track when fact was displayed (before user clicks Continue).

    Args:
        fact_id: ID of the fact that was shown
        user_id: ID of the user

    Returns:
        FactState: The updated FactState object
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(fact_id=fact_id, user_id=user_id)
        db.session.add(state)
    state.last_shown_at = datetime.utcnow()
    db.session.commit()
    return state


def is_fact_learned(fact_id, user_id):
    """
    Check if fact is in learned state for a specific user.

    Args:
        fact_id: ID of the fact to check
        user_id: ID of the user

    Returns:
        bool: True if learned (learned_at is not None), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    return state is not None and state.learned_at is not None


def get_unlearned_facts(domain_id, user_id):
    """
    Get all unlearned facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are unlearned
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    unlearned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()
        if not state or state.learned_at is None:
            unlearned.append(fact)
    return unlearned


def get_learned_facts(domain_id, user_id):
    """
    Get all learned (but not mastered) facts in a domain for a specific user.

    Args:
        domain_id: ID of the domain
        user_id: ID of the user

    Returns:
        list: List of Fact objects that are learned but not mastered
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    learned = []
    for fact in facts:
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()
        if (
            state
            and state.learned_at is not None
            and not get_mastery_status(fact.id, user_id)
        ):
            learned.append(fact)
    return learned


def update_consecutive_attempts(fact_id, correct, user_id):
    """
    Update consecutive correct/wrong counters for a specific user.

    Args:
        fact_id: ID of the fact
        correct: Boolean indicating if attempt was correct
        user_id: ID of the user

    Returns:
        bool: True if should demote to unlearned (2 consecutive wrong), False otherwise
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    if not state:
        state = FactState(
            fact_id=fact_id, user_id=user_id, consecutive_correct=0, consecutive_wrong=0
        )
        db.session.add(state)
        db.session.flush()  # Flush to apply defaults

    if correct:
        state.consecutive_correct += 1
        state.consecutive_wrong = 0  # Reset wrong counter
    else:
        state.consecutive_wrong += 1
        state.consecutive_correct = 0  # Reset correct counter

        # Check if should demote to unlearned (2 consecutive wrong)
        if state.consecutive_wrong >= 2:
            state.learned_at = None  # Demote to unlearned
            state.consecutive_wrong = 0
            state.consecutive_correct = 0
            db.session.commit()
            return True  # Signal demotion

    db.session.commit()
    return False


def has_two_consecutive_correct(fact_id, user_id):
    """
    Check if fact has 2 consecutive correct answers for a specific user.

    Args:
        fact_id: ID of the fact
        user_id: ID of the user

    Returns:
        bool: True if fact has 2+ consecutive correct answers
    """
    state = FactState.query.filter_by(fact_id=fact_id, user_id=user_id).first()
    return state is not None and state.consecutive_correct >= 2


def reset_domain_progress(domain_id, user_id):
    """
    Reset all progress for a domain for a specific user.
    Clears learned status, attempts, and mastery.

    Args:
        domain_id: ID of the domain to reset
        user_id: ID of the user
    """
    facts = Fact.query.filter_by(domain_id=domain_id).all()
    for fact in facts:
        # Delete all attempts by this user
        Attempt.query.filter_by(fact_id=fact.id, user_id=user_id).delete()
        # Delete fact state for this user
        FactState.query.filter_by(fact_id=fact.id, user_id=user_id).delete()
    db.session.commit()


def get_progress_string(domain_id, user_id):
    """
    Generate a progress string showing status of all facts in domain
    for a specific user.

    Returns a string of symbols (·-+*) representing fact states:
    · = unlearned (not shown)
    - = shown (but not learned)
    + = learned (but not mastered)
    * = mastered

    Args:
        domain_id: The domain ID
        user_id: ID of the user

    Returns:
        String of symbols, one per fact (e.g., "·-+*····")
    """
    # Get all facts for domain, ordered by ID for consistency
    domain = Domain.query.get(domain_id)
    if not domain:
        return ""

    facts = Fact.query.filter_by(domain_id=domain_id).order_by(Fact.id).all()

    progress_symbols = []
    for fact in facts:
        # Get fact state for this user
        state = FactState.query.filter_by(fact_id=fact.id, user_id=user_id).first()

        # Determine symbol based on state
        if not state or (state.learned_at is None and state.last_shown_at is None):
            # Unlearned - not shown yet
            symbol = "·"
        elif state.learned_at is None:
            # Shown but not learned
            symbol = "-"
        elif get_mastery_status(fact.id, user_id):
            # Mastered
            symbol = "*"
        else:
            # Learned but not mastered
            symbol = "+"

        progress_symbols.append(symbol)

    return "".join(progress_symbols)


# ============================================================================
# USER MANAGEMENT FUNCTIONS
# ============================================================================


def create_user(
    email, password, role, first_name, last_name, organization_id, created_by_id=None
):
    """
    Create a new user with hashed password.

    Args:
        email: User's email address
        password: Plain text password (will be hashed), or None for token-based setup
        role: User role ('admin', 'teacher', 'student')
        first_name: User's first name
        last_name: User's last name
        organization_id: ID of the organization
        created_by_id: ID of the user who created this user (optional for admin)

    Returns:
        User: The created User object

    Raises:
        ValueError: If email already exists or password is invalid
    """
    from werkzeug.security import generate_password_hash
    import secrets
    from datetime import timedelta

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        raise ValueError("Email already exists")

    # Validate role
    if role not in ["admin", "teacher", "student"]:
        raise ValueError("Role must be 'admin', 'teacher', or 'student'")

    # Handle password or setup token
    password_hash = None
    setup_token = None
    setup_token_expires = None

    if password:
        # Validate password
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Hash password
        password_hash = generate_password_hash(password, method="scrypt")
    else:
        # Generate setup token for first-time login
        setup_token = secrets.token_urlsafe(32)
        setup_token_expires = datetime.utcnow() + timedelta(
            days=7
        )  # Token valid for 7 days

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        first_name=first_name,
        last_name=last_name,
        organization_id=organization_id,
        created_by=created_by_id,
        setup_token=setup_token,
        setup_token_expires=setup_token_expires,
    )

    db.session.add(user)
    db.session.commit()

    return user


def authenticate_user(email, password):
    """
    Authenticate a user by email and password.

    Args:
        email: User's email address
        password: Plain text password

    Returns:
        User: The authenticated User object, or None if authentication fails
    """
    from werkzeug.security import check_password_hash

    user = User.query.filter_by(email=email, is_active=True).first()

    if not user:
        return None

    if not check_password_hash(user.password_hash, password):
        return None

    return user


def get_user_domains(user_id):
    """
    Get all domains assigned to a user.

    Args:
        user_id: ID of the user

    Returns:
        list: List of Domain objects assigned to the user
    """
    assignments = UserDomainAssignment.query.filter_by(user_id=user_id).all()
    domains = [assignment.domain for assignment in assignments]
    return domains


def assign_domain_to_user(user_id, domain_id, assigned_by_id):
    """
    Assign a domain to a user.

    Args:
        user_id: ID of the user (student)
        domain_id: ID of the domain
        assigned_by_id: ID of the user assigning (teacher/admin)

    Returns:
        UserDomainAssignment: The created assignment object

    Raises:
        ValueError: If assignment already exists or domain/user not found
    """
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    # Check if domain exists
    domain = Domain.query.get(domain_id)
    if not domain:
        raise ValueError(f"Domain with ID {domain_id} not found")

    # Check if assignment already exists
    existing = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    if existing:
        raise ValueError("Domain already assigned to user")

    # Create assignment
    assignment = UserDomainAssignment(
        user_id=user_id, domain_id=domain_id, assigned_by=assigned_by_id
    )

    db.session.add(assignment)
    db.session.commit()

    return assignment


def unassign_domain_from_user(user_id, domain_id):
    """
    Unassign a domain from a user.

    Args:
        user_id: ID of the user
        domain_id: ID of the domain

    Returns:
        bool: True if unassigned, False if assignment didn't exist
    """
    assignment = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    if not assignment:
        return False

    db.session.delete(assignment)
    db.session.commit()

    return True


def is_domain_assigned(user_id, domain_id):
    """
    Check if a domain is assigned to a user.

    Args:
        user_id: ID of the user
        domain_id: ID of the domain

    Returns:
        bool: True if domain is assigned to user, False otherwise
    """
    assignment = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    return assignment is not None


def get_students_by_teacher(teacher_id):
    """
    Get all students in the same organization as a teacher.

    Args:
        teacher_id: ID of the teacher

    Returns:
        list: List of User objects (students)
    """
    teacher = User.query.get(teacher_id)
    if not teacher:
        return []

    # Get all students in the same organization
    students = (
        User.query.filter_by(
            organization_id=teacher.organization_id, role="student", is_active=True
        )
        .order_by(User.last_name, User.first_name)
        .all()
    )

    return students


def get_student_progress_summary(student_id):
    """
    Get a summary of a student's progress across all assigned domains.

    Args:
        student_id: ID of the student

    Returns:
        dict: Summary with domain progress information
    """
    student = User.query.get(student_id)
    if not student:
        return None

    # Get assigned domains
    domains = get_user_domains(student_id)

    summary = {"student": student, "domains": []}

    for domain in domains:
        facts = Fact.query.filter_by(domain_id=domain.id).all()
        total_facts = len(facts)

        learned_count = len([f for f in facts if is_fact_learned(f.id, student_id)])
        mastered_count = len([f for f in facts if get_mastery_status(f.id, student_id)])

        # Get attempt count
        attempt_count = sum([get_attempt_count(f.id, student_id) for f in facts])

        # Get progress string
        progress_str = get_progress_string(domain.id, student_id)

        summary["domains"].append(
            {
                "domain": domain,
                "total_facts": total_facts,
                "learned_count": learned_count,
                "mastered_count": mastered_count,
                "attempt_count": attempt_count,
                "progress_string": progress_str,
            }
        )

    return summary


def get_student_domain_progress(student_id, domain_id):
    """
    Get detailed progress for a student in a specific domain.

    Args:
        student_id: ID of the student
        domain_id: ID of the domain

    Returns:
        dict: Detailed progress information
    """
    student = User.query.get(student_id)
    domain = Domain.query.get(domain_id)

    if not student or not domain:
        return None

    facts = Fact.query.filter_by(domain_id=domain_id).all()
    total_facts = len(facts)

    learned_count = len([f for f in facts if is_fact_learned(f.id, student_id)])
    mastered_count = len([f for f in facts if get_mastery_status(f.id, student_id)])
    attempt_count = sum([get_attempt_count(f.id, student_id) for f in facts])

    progress_str = get_progress_string(domain_id, student_id)

    # Get all attempts to calculate time spent
    all_attempts = []
    for fact in facts:
        attempts = Attempt.query.filter_by(fact_id=fact.id, user_id=student_id).all()
        all_attempts.extend(attempts)

    # Sort by timestamp
    all_attempts.sort(key=lambda a: a.timestamp)

    # Calculate time spent (rough estimate based on timestamps)
    time_spent_minutes = 0
    if len(all_attempts) > 1:
        first_attempt = all_attempts[0].timestamp
        last_attempt = all_attempts[-1].timestamp
        time_delta = last_attempt - first_attempt
        time_spent_minutes = int(time_delta.total_seconds() / 60)

    return {
        "student": student,
        "domain": domain,
        "total_facts": total_facts,
        "learned_count": learned_count,
        "mastered_count": mastered_count,
        "attempt_count": attempt_count,
        "time_spent_minutes": time_spent_minutes,
        "progress_string": progress_str,
    }


def get_questions_answered_today(user_id):
    """
    Get the number of questions answered by a user today.

    Args:
        user_id: ID of the user

    Returns:
        int: Number of attempts today
    """
    from datetime import datetime

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    count = Attempt.query.filter(
        Attempt.user_id == user_id, Attempt.timestamp >= today_start
    ).count()

    return count


def get_total_time_spent(user_id):
    """
    Get total estimated time spent by a user across all domains.

    Args:
        user_id: ID of the user

    Returns:
        int: Total minutes spent (rough estimate)
    """
    attempts = (
        Attempt.query.filter_by(user_id=user_id).order_by(Attempt.timestamp).all()
    )

    if len(attempts) < 2:
        return 0

    # Calculate time from first to last attempt
    first_attempt = attempts[0].timestamp
    last_attempt = attempts[-1].timestamp
    time_delta = last_attempt - first_attempt
    total_minutes = int(time_delta.total_seconds() / 60)

    return total_minutes


def get_unique_session_count(user_id):
    """
    Get the number of unique quiz sessions for a user.

    Args:
        user_id: ID of the user

    Returns:
        int: Number of unique sessions
    """
    # Count distinct session_ids
    result = (
        db.session.query(Attempt.session_id)
        .filter(Attempt.user_id == user_id, Attempt.session_id.isnot(None))
        .distinct()
        .count()
    )

    return result


def format_time_spent(minutes):
    """
    Format minutes into a readable string.

    Args:
        minutes: Number of minutes

    Returns:
        str: Formatted time (e.g., "1h 30m", "45m")
    """
    if minutes < 60:
        return f"{minutes}m"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h {remaining_minutes}m"
