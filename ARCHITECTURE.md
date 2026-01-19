# Rememberizer Architecture & Technical Documentation

Comprehensive technical documentation of Rememberizer's architecture, design decisions, and implementation details.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Database Design](#database-design)
3. [Authentication System](#authentication-system)
4. [Authorization System](#authorization-system)
5. [Quiz Logic](#quiz-logic)
6. [Learning State Machine](#learning-state-machine)
7. [Code Organization](#code-organization)
8. [API Routes](#api-routes)
9. [Data Flow](#data-flow)
10. [Design Decisions](#design-decisions)
11. [Performance Considerations](#performance-considerations)
12. [Extensibility](#extensibility)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                        │
│  (Web Browser - HTML/CSS/JS with Terminal Aesthetic)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Web Server Layer                          │
│  Flask Development Server (dev) or Gunicorn/Waitress (prod)│
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   app.py     │  │   auth.py    │  │ quiz_logic.py│     │
│  │  (Routes &   │  │ (Flask-Login │  │  (Question   │     │
│  │   Request    │  │  & Authz)    │  │  Generation) │     │
│  │  Handlers)   │  │              │  │              │     │
│  └──────┬───────┘  └───────┬──────┘  └──────┬───────┘     │
│         │                  │                 │             │
│         └──────────────────┼─────────────────┘             │
│                            ▼                               │
│              ┌──────────────────────────┐                  │
│              │      models.py           │                  │
│              │  (Database Models &      │                  │
│              │   Business Logic)        │                  │
│              └──────────┬───────────────┘                  │
└─────────────────────────┼───────────────────────────────────┘
                          │ SQLAlchemy ORM
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  SQLite (dev) or PostgreSQL (prod) - Relational Database   │
│  Tables: users, organizations, user_domain_assignments,     │
│          domains, facts, fact_states, attempts              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Python 3.8+**: Core language
- **Flask 2.3+**: Web framework (micro-framework, unopinionated)
- **Flask-SQLAlchemy 3.0+**: ORM for database access
- **Flask-Login 0.6+**: Session management and user authentication
- **Werkzeug 2.3+**: WSGI utilities, password hashing (scrypt)

**Database:**
- **SQLite**: Development/small deployments (single-file, zero-config)
- **PostgreSQL**: Production/large deployments (concurrent access, ACID compliance)

**Frontend:**
- **HTML5**: Semantic markup
- **CSS3**: Terminal-style aesthetics (green-on-black, monospace fonts)
- **Vanilla JavaScript**: Minimal client-side interactivity (no frameworks)
- **Jinja2**: Server-side templating (Flask built-in)

**Testing:**
- **pytest 7.4+**: Test framework
- **pytest-flask 1.2+**: Flask testing utilities
- **pytest-cov 4.1+**: Code coverage reporting

**Code Quality:**
- **Black 23.0+**: Code formatter (opinionated, consistent)
- **Flake8 6.0+**: Linter (PEP 8 compliance)

### Deployment Architecture (Production)

```
                  ┌──────────────┐
                  │   Internet   │
                  └──────┬───────┘
                         │ HTTPS (443)
                         ▼
              ┌─────────────────────┐
              │   Nginx/Apache      │
              │  (Reverse Proxy     │
              │   & SSL Termination)│
              └──────────┬──────────┘
                         │ HTTP (8000)
                         ▼
              ┌─────────────────────┐
              │  Gunicorn/uWSGI     │
              │  (WSGI Server       │
              │   4 workers)        │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Flask App          │
              │  (Application Code) │
              └──────────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │PostgreSQL│  │File System│ │ Logs     │
   │ Database │  │ (static/  │ │ (stdout/ │
   │          │  │ templates)│ │ files)   │
   └──────────┘  └──────────┘  └──────────┘
```

**Process Management:**
- **Supervisor** or **systemd**: Ensure Flask app stays running
- **Automatic restart**: On crashes or server reboot
- **Log rotation**: Prevent disk space exhaustion

---

## Database Design

### Entity-Relationship Diagram

```
┌─────────────────┐
│  organizations  │
│─────────────────│        ┌─────────────────┐
│ id (PK)         │◄───────│     users       │
│ name            │        │─────────────────│
│ created_at      │        │ id (PK)         │
└─────────────────┘        │ email (UNIQUE)  │
                           │ password_hash   │
                           │ role            │
                           │ first_name      │
                           │ last_name       │
                           │ organization_id │─────┐
                           │ created_by      │─┐   │
                           │ created_at      │ │   │
                           │ last_active     │ │   │
                           │ is_active       │ │   │
                           │ setup_token     │ │   │
                           │ setup_token_exp │ │   │
                           └────────┬────────┘ │   │
                                    │          │   │
                      ┌─────────────┼──────────┘   │
                      │             │              │
                      │             │              │
        ┌─────────────▼─────────────▼────┐         │
        │ user_domain_assignments        │         │
        │────────────────────────────────│         │
        │ id (PK)                        │         │
        │ user_id (FK → users.id)        │         │
        │ domain_id (FK → domains.id)────┼───┐     │
        │ assigned_by (FK → users.id)    │   │     │
        │ assigned_at                    │   │     │
        │ UNIQUE(user_id, domain_id)     │   │     │
        └────────────────────────────────┘   │     │
                                              │     │
                  ┌───────────────────────────┘     │
                  │                                 │
                  ▼                                 │
        ┌─────────────────┐                        │
        │    domains      │                        │
        │─────────────────│                        │
        │ id (PK)         │                        │
        │ name            │                        │
        │ filename        │                        │
        │ field_names     │                        │
        └────────┬────────┘                        │
                 │                                  │
                 │                                  │
                 ▼                                  │
        ┌─────────────────┐                        │
        │     facts       │                        │
        │─────────────────│                        │
        │ id (PK)         │                        │
        │ domain_id (FK)  │                        │
        │ fact_data (JSON)│                        │
        └────────┬────────┘                        │
                 │                                  │
      ┌──────────┼──────────────────┐              │
      ▼          ▼                  ▼              │
┌─────────────────┐     ┌───────────────────┐     │
│  fact_states    │     │    attempts       │     │
│─────────────────│     │───────────────────│     │
│ id (PK)         │     │ id (PK)           │     │
│ fact_id (FK)    │     │ fact_id (FK)      │     │
│ user_id (FK)────┼─────│ user_id (FK)──────┼─────┘
│ learned_at      │     │ field_name        │
│ last_shown_at   │     │ correct           │
│ consecutive_cor │     │ timestamp         │
│ consecutive_wrg │     │ session_id        │
│ created_at      │     └───────────────────┘
│ updated_at      │
│ UNIQUE(fact_id, │
│        user_id) │
└─────────────────┘
```

### Table Descriptions

#### 1. organizations
**Purpose**: Support multi-tenant architecture (currently single organization).

**Columns:**
- `id`: Primary key, auto-increment
- `name`: Organization name (UNIQUE constraint)
- `created_at`: Timestamp of organization creation

**Relationships:**
- One-to-many with `users`

**Future**: Add `subdomain`, `settings`, `plan_tier` columns for SaaS expansion.

#### 2. users
**Purpose**: Store user accounts with authentication and metadata.

**Columns:**
- `id`: Primary key, auto-increment
- `email`: Unique email address (INDEXED for fast login lookups)
- `password_hash`: Scrypt-hashed password (NULL during setup phase)
- `role`: Enum-like string ('admin', 'teacher', 'student')
- `first_name`, `last_name`: User's full name
- `organization_id`: Foreign key to organizations (enables multi-tenant)
- `created_by`: Foreign key to users (audit trail: who created this account)
- `created_at`: Account creation timestamp
- `last_active`: Last request timestamp (updated via before_request hook)
- `is_active`: Boolean flag (FALSE = deactivated, cannot login)
- `setup_token`: UUID token for password setup (NULL after setup)
- `setup_token_expires`: Token expiration (7 days from creation)

**Relationships:**
- Many-to-one with `organizations`
- Many-to-one with `users` (self-referential, created_by)
- One-to-many with `user_domain_assignments`
- One-to-many with `fact_states`
- One-to-many with `attempts`

**Indexes:**
- `email` (UNIQUE INDEX): Fast login lookups
- `organization_id` (INDEX): Fast organization filtering

#### 3. user_domain_assignments
**Purpose**: Track which domains are assigned to which students.

**Columns:**
- `id`: Primary key, auto-increment
- `user_id`: Foreign key to users (the student)
- `domain_id`: Foreign key to domains
- `assigned_by`: Foreign key to users (the teacher who assigned)
- `assigned_at`: Timestamp of assignment

**Constraints:**
- **UNIQUE(user_id, domain_id)**: Prevents duplicate assignments

**Relationships:**
- Many-to-one with `users` (student)
- Many-to-one with `users` (teacher, via assigned_by)
- Many-to-one with `domains`

**Indexes:**
- `user_id` (INDEX): Fast "get all domains for student" queries
- `domain_id` (INDEX): Fast "get all students for domain" queries

#### 4. domains
**Purpose**: Store fact domains (loaded from JSON files).

**Columns:**
- `id`: Primary key, auto-increment
- `name`: Domain name (e.g., "Greek Muses")
- `filename`: Source JSON filename (e.g., "greek_muses.json")
- `field_names`: JSON array of field names (e.g., ["name", "domain_of_expertise"])

**Relationships:**
- One-to-many with `facts`
- One-to-many with `user_domain_assignments`

**Note**: Domains are loaded from `facts/*.json` on application startup.

#### 5. facts
**Purpose**: Store individual facts within domains.

**Columns:**
- `id`: Primary key, auto-increment
- `domain_id`: Foreign key to domains
- `fact_data`: JSON object with fact field values

**Example fact_data:**
```json
{
  "name": "Calliope",
  "domain_of_expertise": "Epic Poetry",
  "symbol": "Writing Tablet"
}
```

**Relationships:**
- Many-to-one with `domains`
- One-to-many with `fact_states`
- One-to-many with `attempts`

#### 6. fact_states
**Purpose**: Track learning state for each user-fact combination.

**Columns:**
- `id`: Primary key, auto-increment
- `fact_id`: Foreign key to facts
- `user_id`: Foreign key to users
- `learned_at`: Timestamp when marked as learned (NULL = unlearned)
- `last_shown_at`: Timestamp when fact was last displayed
- `consecutive_correct`: Counter for consecutive correct answers (0-N)
- `consecutive_wrong`: Counter for consecutive wrong answers (0-N)
- `created_at`: Record creation timestamp
- `updated_at`: Last update timestamp

**Constraints:**
- **UNIQUE(fact_id, user_id)**: One state per user per fact

**Relationships:**
- Many-to-one with `facts`
- Many-to-one with `users`

**Indexes:**
- `user_id` (INDEX): Fast "get all states for user" queries
- `fact_id` (INDEX): Fast "get state for fact" queries

**State Logic:**
- `learned_at IS NULL` → Unlearned
- `learned_at IS NOT NULL` → Learned
- Mastered is computed from `attempts` table (6/7 correct)

#### 7. attempts
**Purpose**: Record every quiz attempt for analytics and mastery calculation.

**Columns:**
- `id`: Primary key, auto-increment
- `fact_id`: Foreign key to facts (which fact was quizzed)
- `field_name`: Which field was asked (e.g., "domain_of_expertise")
- `correct`: Boolean (TRUE = correct answer, FALSE = incorrect)
- `timestamp`: Attempt timestamp
- `user_id`: Foreign key to users (who answered)
- `session_id`: UUID for quiz session (tracks practice sessions)

**Relationships:**
- Many-to-one with `facts`
- Many-to-one with `users`

**Indexes:**
- `user_id` (INDEX): Fast "get all attempts for user" queries
- `fact_id` (INDEX): Fast "get attempts for fact" queries
- `session_id` (INDEX): Fast session-based queries

**Analytics Use Cases:**
- Mastery calculation: Last 7 attempts for fact/user
- Engagement metrics: Count attempts, calculate time deltas
- Session tracking: Group attempts by session_id

---

## Authentication System

### Token-Based Password Setup Flow

```
┌─────────────┐
│  Admin      │
│  Creates    │
│  Teacher    │
└──────┬──────┘
       │
       │ POST /admin/teachers/create
       │ {first_name, last_name, email}
       ▼
┌────────────────────────────────────┐
│  models.create_user()              │
│  - Validates email format          │
│  - Checks for duplicate email      │
│  - Creates User record             │
│  - password_hash = NULL            │
│  - setup_token = uuid4()           │
│  - setup_token_expires = now + 7d  │
└──────────┬─────────────────────────┘
           │
           │ Returns User object
           ▼
┌────────────────────────────────────┐
│  send_user_setup_notification()    │
│  - Generates setup URL             │
│  - Attempts email send             │
│  - If success: Flash "email sent"  │
│  - If fail: Flash link to share    │
└──────────┬─────────────────────────┘
           │
           │ Email or manual share
           ▼
┌─────────────┐
│  Teacher    │
│  Receives   │
│  Magic Link │
└──────┬──────┘
       │
       │ Clicks link
       │ GET /setup-password/<token>
       ▼
┌────────────────────────────────────┐
│  setup_password() route            │
│  - Validates token exists          │
│  - Checks token not expired        │
│  - Checks user not already active  │
│  - Displays password form          │
└──────────┬─────────────────────────┘
           │
           │ User enters password
           │ POST /setup-password/<token>
           │ {password, confirm_password}
           ▼
┌────────────────────────────────────┐
│  setup_password_submit() route     │
│  - Validates passwords match       │
│  - Validates min 8 chars           │
│  - Hashes password (scrypt)        │
│  - Sets user.password_hash         │
│  - Clears setup_token              │
│  - Clears setup_token_expires      │
│  - Commits to database             │
└──────────┬─────────────────────────┘
           │
           │ Redirect to /login
           ▼
┌─────────────┐
│  Teacher    │
│  Can Now    │
│  Login      │
└─────────────┘
```

### Session Management with Flask-Login

**Authentication on Login:**
```python
# In /login route:
user = authenticate_user(email, password)
if user:
    auth_user = AuthUser(user)
    login_user(auth_user, remember=True)
    # Session cookie created automatically
```

**Session Validation on Every Request:**
```python
# Flask-Login automatically:
1. Reads session cookie
2. Calls @login_manager.user_loader(user_id)
3. Loads User object from database
4. Sets flask_login.current_user
5. If invalid/expired: current_user = AnonymousUser
```

**Accessing Current User:**
```python
from flask_login import current_user

# In any route:
if current_user.is_authenticated:
    user_id = current_user.id
    role = current_user.role
    email = current_user.email
```

**Logout:**
```python
# In /logout route:
logout_user()
# Clears session cookie
# current_user becomes AnonymousUser
```

### Password Security

**Hashing Algorithm:**
- **Werkzeug scrypt**: PBKDF2-based, industry-standard
- **Auto-salted**: Unique salt per password
- **Slow by design**: Resistant to brute-force attacks

**Hashing:**
```python
from werkzeug.security import generate_password_hash

password_hash = generate_password_hash(password, method='scrypt')
# Returns: 'scrypt:32768:8:1$<salt>$<hash>'
```

**Verification:**
```python
from werkzeug.security import check_password_hash

is_valid = check_password_hash(stored_hash, entered_password)
# Uses constant-time comparison (prevents timing attacks)
```

**Security Properties:**
- **No plaintext storage**: Only hash stored in database
- **One-way function**: Cannot reverse hash to get password
- **Salt per password**: Prevents rainbow table attacks
- **Slow hashing**: Makes brute-force expensive (intentionally slow)

---

## Authorization System

### Role-Based Access Control (RBAC)

**Decorator-Based Authorization:**

```python
# In auth.py:
def role_required(*roles):
    """
    Decorator to require specific role(s).
    Usage: @role_required('admin', 'teacher')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                abort(403)  # Forbidden
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

**Usage in Routes:**

```python
@app.route("/admin/dashboard")
@role_required('admin')
def admin_dashboard():
    # Only admins can access
    pass

@app.route("/teacher/dashboard")
@role_required('teacher', 'admin')
def teacher_dashboard():
    # Teachers and admins can access
    pass

@app.route("/student/domains")
@login_required
def student_domains():
    # Any authenticated user can access
    # But we check role inside:
    if current_user.role != 'student':
        abort(403)
    pass
```

### Domain Assignment Enforcement

**Before starting quiz:**
```python
@app.route("/start", methods=["POST"])
@login_required
def start():
    domain_id = request.form.get("domain_id")

    # Students must have domain assigned
    if current_user.role == 'student':
        if not is_domain_assigned(current_user.id, domain_id):
            flash("You don't have access to this domain", "error")
            return redirect(url_for('student_domains'))

    # Admin/teacher can access any domain
    # Continue with quiz...
```

**Domain list filtering:**
```python
@app.route("/student/domains")
@login_required
def student_domains():
    if current_user.role != 'student':
        abort(403)

    # Only show assigned domains
    assigned_domains = get_user_domains(current_user.id)
    # Returns only domains in user_domain_assignments table
```

### Organization Isolation

**Teacher can only see their org's students:**
```python
@app.route("/teacher/dashboard")
@role_required('teacher', 'admin')
def teacher_dashboard():
    # Get students in same organization
    students = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='student'
    ).all()
    # Students from other orgs are not visible
```

**Cross-org access protection:**
```python
@app.route("/teacher/students/<int:student_id>")
@role_required('teacher', 'admin')
def view_student(student_id):
    student = User.query.get_or_404(student_id)

    # Verify student is in same organization
    if student.organization_id != current_user.organization_id:
        abort(403)

    # Continue...
```

---

## Quiz Logic

### Question Generation Algorithm

**Function**: `prepare_quiz_question_for_fact(fact, domain_id, last_question_key, user_id)`

**Steps:**

1. **Select Random Field to Quiz:**
   ```python
   field_names = get_field_names_for_domain(domain_id)
   available_fields = [f for f in field_names if f != last_question_key]
   question_field = random.choice(available_fields or field_names)
   ```

2. **Get Correct Answer:**
   ```python
   correct_answer = fact.fact_data[question_field]
   ```

3. **Generate Wrong Answers:**
   ```python
   all_facts = Fact.query.filter_by(domain_id=domain_id).all()
   other_facts = [f for f in all_facts if f.id != fact.id]
   random.shuffle(other_facts)
   wrong_answers = [f.fact_data[question_field] for f in other_facts[:3]]
   # Takes first 3 shuffled facts as wrong answers
   ```

4. **Shuffle All Options:**
   ```python
   options = [correct_answer] + wrong_answers
   random.shuffle(options)
   correct_index = options.index(correct_answer)
   ```

5. **Return Question Data:**
   ```python
   return {
       'fact_id': fact.id,
       'question_field': question_field,
       'options': options,
       'correct_index': correct_index
   }
   ```

### Fact Selection Logic

**Selecting Next Fact to Quiz:**

**Function**: `get_next_unlearned_fact(domain_id, user_id)`

**Returns**: Next unlearned fact, or None if all learned.

**Priority:**
1. Facts never shown (`last_shown_at IS NULL`)
2. Facts shown but not learned (`learned_at IS NULL AND last_shown_at IS NOT NULL`)
3. None if all facts are learned

**Selecting Fact to Quiz from Learned Facts:**

**Function**: `select_quiz_fact(domain_id, excluded_ids, user_id)`

**Returns**: Fact to quiz (prioritizes least-practiced).

**Logic:**
1. Get all learned facts for domain/user
2. Exclude facts in `excluded_ids` (recently quizzed)
3. For each fact, count total attempts
4. Sort by attempt count (ascending)
5. Return fact with fewest attempts

**Result**: Balances practice across all learned facts.

### Spaced Repetition (Every 3rd Question)

**Implementation in `/quiz` route:**

```python
question_count = session.get("question_count", 0)
is_reinforcement_question = (question_count % 3 == 0 and question_count > 0)

if is_reinforcement_question:
    # Select from mastered facts
    fact = select_recovery_fact(domain_id, excluded_ids, user_id)
    if fact:
        # Quiz this mastered fact for reinforcement
    else:
        # No mastered facts, select normal fact
```

**`select_recovery_fact(domain_id, excluded_ids, user_id)`:**

**Returns**: Random mastered fact, or None.

**Logic:**
1. Get all learned facts for domain/user
2. Filter to mastered facts (6/7 correct with most recent correct)
3. Exclude facts in `excluded_ids`
4. Return random choice

**Result**: Every 3rd question reviews a mastered fact to prevent forgetting.

---

## Learning State Machine

### State Diagram

```
             ┌─────────────┐
             │  UNLEARNED  │
             │ (learned_at │
             │  = NULL)    │
             └──────┬──────┘
                    │
                    │ User views fact
                    │ Clicks "Continue"
                    │ mark_fact_learned()
                    ▼
             ┌─────────────┐
             │   LEARNED   │
             │ (learned_at │
             │  = datetime)│
             └──────┬──────┘
                    │
                    │ Answer questions
                    │ Achieve 6/7 correct
                    │ with most recent correct
                    ▼
             ┌─────────────┐
             │  MASTERED   │
             │ (computed   │
             │  state)     │
             └──────┬──────┘
                    │
                    │ 2 consecutive
     ┌──────────────┤ wrong answers
     │              │ update_consecutive_attempts()
     │              ▼
     │       ┌─────────────┐
     └──────►│  UNLEARNED  │
             │ (demoted)   │
             └─────────────┘
```

### State Transition Functions

#### 1. Unlearned → Learned

**Trigger**: User views fact and clicks "Continue".

**Functions Called:**
```python
mark_fact_shown(fact_id, user_id)
# Sets last_shown_at = datetime.utcnow()

mark_fact_learned(fact_id, user_id)
# Sets learned_at = datetime.utcnow()
# Resets consecutive_correct and consecutive_wrong to 0
```

**Database Changes:**
```sql
UPDATE fact_states
SET learned_at = NOW(),
    last_shown_at = NOW(),
    consecutive_correct = 0,
    consecutive_wrong = 0
WHERE fact_id = ? AND user_id = ?
```

#### 2. Learned → Mastered

**Trigger**: Achieve 6/7 correct in last 7 attempts, most recent correct.

**Computation** (not a database state):
```python
def get_mastery_status(fact_id, user_id):
    attempts = Attempt.query.filter_by(
        fact_id=fact_id,
        user_id=user_id
    ).order_by(Attempt.timestamp.desc()).limit(7).all()

    if len(attempts) < 7:
        return False  # Not enough attempts

    correct_count = sum(1 for a in attempts if a.correct)
    most_recent_correct = attempts[0].correct

    return correct_count >= 6 and most_recent_correct
```

**No database change** (mastered is computed on-the-fly).

#### 3. Learned/Mastered → Unlearned (Demotion)

**Trigger**: 2 consecutive wrong answers.

**Function Called:**
```python
update_consecutive_attempts(fact_id, False, user_id)
# Increments consecutive_wrong
# Resets consecutive_correct to 0

# Inside update_consecutive_attempts:
if state.consecutive_wrong >= 2:
    state.learned_at = None  # Demote to unlearned
    state.consecutive_correct = 0
    state.consecutive_wrong = 0
```

**Database Changes:**
```sql
-- First wrong answer:
UPDATE fact_states
SET consecutive_wrong = consecutive_wrong + 1,
    consecutive_correct = 0
WHERE fact_id = ? AND user_id = ?

-- Second consecutive wrong answer:
UPDATE fact_states
SET learned_at = NULL,  -- Demote!
    consecutive_correct = 0,
    consecutive_wrong = 0
WHERE fact_id = ? AND user_id = ?
```

### Consecutive Answer Tracking

**On Correct Answer:**
```python
record_attempt(fact_id, field_name, True, user_id, session_id)
update_consecutive_attempts(fact_id, True, user_id)

# Inside update_consecutive_attempts:
state.consecutive_correct += 1
state.consecutive_wrong = 0  # Reset wrong counter
```

**On Incorrect Answer:**
```python
record_attempt(fact_id, field_name, False, user_id, session_id)
update_consecutive_attempts(fact_id, False, user_id)

# Inside update_consecutive_attempts:
state.consecutive_wrong += 1
state.consecutive_correct = 0  # Reset correct counter

if state.consecutive_wrong >= 2:
    # Demote to unlearned
    state.learned_at = None
    state.consecutive_correct = 0
    state.consecutive_wrong = 0
```

**Progression Logic (in answer route):**
```python
if is_correct:
    if has_two_consecutive_correct(fact_id, user_id):
        # Move to next fact
        session.pop("pending_fact_id", None)
    else:
        # Quiz same fact again (need 2 correct)
        session["pending_fact_id"] = fact_id
else:
    if state.consecutive_wrong >= 2:
        # Show fact again (demoted)
        return redirect(url_for('show_fact', fact_id=fact_id))
    else:
        # Show fact, then re-quiz
        return redirect(url_for('show_fact', fact_id=fact_id))
```

---

## Code Organization

### File Structure

```
rememberizer/
├── app.py                  # Main application (routes, config, startup)
├── models.py               # Database models + business logic
├── auth.py                 # Authentication (Flask-Login, decorators)
├── quiz_logic.py           # Quiz generation (question/fact selection)
├── facts_loader.py         # JSON fact loading + validation
├── init_database.py        # Database initialization script
├── migration_*.py          # Database migration scripts
├── templates/              # Jinja2 templates (HTML)
│   ├── base.html           # Base template (header, nav, logout)
│   ├── login.html
│   ├── setup_password.html
│   ├── admin/              # Admin templates
│   │   ├── dashboard.html
│   │   └── create_teacher.html
│   ├── teacher/            # Teacher templates
│   │   ├── dashboard.html
│   │   ├── student_detail.html
│   │   └── create_student.html
│   ├── student/            # Student templates
│   │   ├── domains.html
│   │   └── progress.html
│   ├── quiz.html           # Quiz question page
│   ├── show_fact.html      # Fact display page
│   └── answer_result.html  # Answer feedback page
├── static/                 # Static assets
│   ├── style.css           # Terminal-style CSS
│   └── app.js              # Client-side JavaScript
└── tests/                  # Test suite (162+ tests)
    ├── conftest.py         # Pytest fixtures
    ├── test_auth.py
    ├── test_authorization.py
    ├── test_multi_user.py
    ├── test_models.py
    ├── test_quiz_logic.py
    ├── test_template_filters.py
    ├── test_doom_loop.py
    ├── test_facts_loader.py
    └── test_routes.py
```

### Separation of Concerns

**app.py (Routes & Request Handling):**
- Flask app configuration
- Route definitions
- Request/response handling
- Session management
- Template rendering
- Flash messages
- Redirects
- **NO business logic** (delegates to models.py, quiz_logic.py)

**models.py (Business Logic & Data Access):**
- Database model definitions (SQLAlchemy)
- All database queries
- State management functions
- User creation/authentication
- Progress tracking
- Engagement metrics
- **NO Flask dependencies** (pure Python + SQLAlchemy)

**auth.py (Authentication & Authorization):**
- Flask-Login configuration
- AuthUser wrapper class
- user_loader callback
- `@login_required` decorator
- `@role_required` decorator
- `get_current_user()` helper
- **Minimal business logic** (mostly authentication flow)

**quiz_logic.py (Quiz Generation):**
- Question generation
- Fact selection algorithms
- Wrong answer generation
- Option shuffling
- **NO database access** (receives data from models.py)
- **NO Flask dependencies** (pure Python functions)

**facts_loader.py (Data Loading):**
- JSON file parsing
- Domain/fact validation
- Database population
- **Called only on startup**

### Dependency Flow

```
app.py
  ├─► auth.py (authentication decorators)
  ├─► models.py (database queries)
  ├─► quiz_logic.py (question generation)
  └─► facts_loader.py (startup only)

models.py
  └─► db (SQLAlchemy, no other dependencies)

auth.py
  ├─► flask_login (session management)
  └─► models.py (User model)

quiz_logic.py
  └─► random (no other dependencies)

facts_loader.py
  ├─► models.py (Domain, Fact models)
  └─► json (parsing)
```

**Benefits:**
- **Testability**: Each module can be tested independently
- **Maintainability**: Changes to one module don't ripple to others
- **Clarity**: Clear responsibility for each file
- **Reusability**: quiz_logic.py could be used in CLI tool, API, etc.

---

## API Routes

### Route Summary

**Public Routes (No Auth):**
- `GET /` - Redirect to role-specific dashboard
- `GET /login` - Login form
- `POST /login` - Process login
- `GET /logout` - Logout
- `GET /setup-password/<token>` - Password setup form
- `POST /setup-password/<token>` - Process password setup

**Admin Routes (`@role_required('admin')`):**
- `GET /admin/dashboard` - Admin control panel
- `GET /admin/teachers/create` - Create teacher form
- `POST /admin/teachers/create` - Process teacher creation
- `POST /admin/teachers/<id>/deactivate` - Deactivate teacher

**Teacher Routes (`@role_required('teacher', 'admin')`):**
- `GET /teacher/dashboard` - Student list with progress
- `GET /teacher/students/create` - Create student form
- `POST /teacher/students/create` - Process student creation
- `GET /teacher/students/<id>` - Student detail view
- `POST /teacher/students/<id>/assign` - Assign domain
- `POST /teacher/students/<id>/unassign` - Unassign domain
- `POST /teacher/students/<id>/reset-domain/<domain_id>` - Reset progress
- `POST /teacher/students/<id>/deactivate` - Deactivate student
- `GET /teacher/domains` - View all domains

**Student Routes (`@login_required`):**
- `GET /student/domains` - Assigned domain list
- `GET /student/progress` - Personal progress overview

**Quiz Routes (`@login_required`):**
- `POST /start` - Start quiz for domain
- `GET /quiz` - Get next quiz question
- `POST /answer` - Submit answer
- `GET /show_fact/<id>` - View fact card
- `POST /mark_learned/<id>` - Mark fact as learned
- `POST /reset_domain` - Reset domain progress (from quiz)
- `POST /reset_domain_from_menu/<domain_id>` - Reset from menu

### Route Details (Selected Examples)

#### POST /login

**Purpose**: Authenticate user and create session.

**Request:**
```
POST /login
Content-Type: application/x-www-form-urlencoded

email=teacher@example.com&password=mypassword123
```

**Processing:**
1. Extract email and password from form
2. Call `authenticate_user(email, password)`:
   - Look up user by email
   - Verify password hash
   - Check `is_active=TRUE`
   - Return User object or None
3. If authentication succeeds:
   - Create `AuthUser` wrapper
   - Call `login_user(auth_user, remember=True)`
   - Redirect based on role:
     - Admin → `/admin/dashboard`
     - Teacher → `/teacher/dashboard`
     - Student → `/student/domains`
4. If authentication fails:
   - Flash error message
   - Redirect back to `/login`

**Response:**
```
302 Found
Location: /teacher/dashboard
Set-Cookie: session=<encrypted-session-data>; HttpOnly; Path=/
```

#### POST /teacher/students/create

**Purpose**: Create student account with token-based setup.

**Request:**
```
POST /teacher/students/create
Content-Type: application/x-www-form-urlencoded

first_name=Alice&last_name=Johnson&email=alice@example.com
```

**Processing:**
1. Verify current user is teacher or admin
2. Extract form data
3. Call `create_user()`:
   - Validate email format
   - Check for duplicate email
   - Create User record with `password_hash=NULL`
   - Generate `setup_token` (UUID)
   - Set `setup_token_expires` (7 days)
   - Set `created_by=current_user.id`
   - Commit to database
4. Call `send_user_setup_notification()`:
   - Generate setup URL
   - Attempt email send
   - Flash appropriate messages
5. Redirect to teacher dashboard

**Response:**
```
302 Found
Location: /teacher/dashboard
Set-Cookie: session=...
```

**Flash Messages:**
- Success: "Student Alice Johnson created! Setup email sent to alice@example.com"
- Or: "Student Alice Johnson created successfully!" + setup link display

#### POST /answer

**Purpose**: Process quiz answer, update state, return result.

**Request:**
```
POST /answer
Content-Type: application/x-www-form-urlencoded

answer_index=0
```

**Session State:**
```python
session = {
    "current_fact_id": 42,
    "question_field": "domain_of_expertise",
    "correct_index": 2,
    "options": ["Epic Poetry", "Dance", "Lyric Poetry", "Tragedy"],
    "domain_id": 1,
    "quiz_session_id": "550e8400-e29b-41d4-a716-446655440000",
    "question_count": 5
}
```

**Processing:**
1. Extract answer_index from form
2. Get correct_index from session
3. Determine if answer is correct: `is_correct = (answer_index == correct_index)`
4. Record attempt:
   ```python
   record_attempt(
       fact_id=session["current_fact_id"],
       field_name=session["question_field"],
       correct=is_correct,
       user_id=current_user.id,
       session_id=session["quiz_session_id"]
   )
   ```
5. Update consecutive counters:
   ```python
   update_consecutive_attempts(
       fact_id=session["current_fact_id"],
       correct=is_correct,
       user_id=current_user.id
   )
   ```
6. Check if demoted (2 consecutive wrong):
   - If yes: Redirect to `/show_fact/<id>` (review fact)
7. Check if 2 consecutive correct:
   - If yes: Clear `pending_fact_id` (move to next)
   - If no: Set `pending_fact_id` (quiz again)
8. Render answer result template with feedback

**Response:**
```
200 OK
Content-Type: text/html

<html>
  <!-- answer_result.html rendered -->
  <h2>✓ CORRECT!</h2>
  <p>The correct answer is: Lyric Poetry</p>
  <a href="/quiz">[NEXT QUESTION]</a>
</html>
```

---

## Data Flow

### Quiz Session Data Flow

```
┌────────────────────────────────────────────────────────────┐
│  1. Student clicks [START PRACTICE]                        │
│     POST /start (domain_id=1)                              │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  2. /start route:                                          │
│     - Verify domain assignment (students only)             │
│     - Generate session["quiz_session_id"] = UUID           │
│     - Get next unlearned fact from models.py               │
│     - Store domain_id in session                           │
│     - Redirect to /show_fact/<id> or /quiz                 │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  3. /show_fact/<id> route (if unlearned fact exists):     │
│     - Fetch fact from database                             │
│     - Call mark_fact_shown(fact_id, user_id)               │
│     - Render show_fact.html template                       │
│     - Display fact card with [CONTINUE] button             │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ User clicks [CONTINUE]
                        ▼
┌────────────────────────────────────────────────────────────┐
│  4. POST /mark_learned/<id>:                               │
│     - Call mark_fact_learned(fact_id, user_id)             │
│     - Update fact_states: learned_at = NOW()               │
│     - Redirect to /quiz                                    │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  5. GET /quiz route:                                       │
│     - Check if reinforcement question (every 3rd)          │
│     - Select fact to quiz:                                 │
│       • If reinforcement: select_recovery_fact()           │
│       • Else if pending_fact_id: use pending fact          │
│       • Else: select_quiz_fact() (least-practiced)         │
│     - Generate question via prepare_quiz_question()        │
│     - Store question data in session:                      │
│       • current_fact_id                                    │
│       • question_field                                     │
│       • options                                            │
│       • correct_index                                      │
│     - Increment question_count                             │
│     - Render quiz.html template                            │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ User selects answer, clicks [SUBMIT]
                        ▼
┌────────────────────────────────────────────────────────────┐
│  6. POST /answer:                                          │
│     - Compare answer_index with correct_index              │
│     - record_attempt(fact_id, field, correct, user_id,     │
│                      session_id)                           │
│     - update_consecutive_attempts(fact_id, correct,        │
│                                   user_id)                 │
│     - Check for demotion (2 consecutive wrong):            │
│       • If demoted: Redirect to /show_fact/<id>            │
│     - Check for 2 consecutive correct:                     │
│       • If yes: Clear pending_fact_id (move to next)       │
│       • If no: Set pending_fact_id (quiz again)            │
│     - Render answer_result.html with feedback              │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ User clicks [NEXT QUESTION]
                        ▼
                   (Back to step 5)
```

### Database Query Flow Example

**Teacher views student progress:**

```
┌────────────────────────────────────────────────────────────┐
│  GET /teacher/students/<id>                                │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  app.py: view_student(student_id) route                    │
│  1. Fetch student: User.query.get_or_404(student_id)       │
│  2. Verify org: student.organization_id == current_user... │
│  3. Get assigned domains: get_user_domains(student_id)     │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  models.py: get_user_domains(user_id)                      │
│  Query:                                                    │
│    SELECT domains.*                                        │
│    FROM domains                                            │
│    JOIN user_domain_assignments                            │
│      ON domains.id = user_domain_assignments.domain_id     │
│    WHERE user_domain_assignments.user_id = ?               │
│  Returns: [Domain, Domain, ...]                            │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ For each domain:
                        ▼
┌────────────────────────────────────────────────────────────┐
│  models.py: get_student_domain_progress(user_id, domain_id)│
│  Queries:                                                  │
│  1. Total facts: Fact.query.filter_by(domain_id=?).count() │
│  2. Learned count:                                         │
│      SELECT COUNT(*) FROM fact_states                      │
│      WHERE user_id=? AND domain_id=?                       │
│            AND learned_at IS NOT NULL                      │
│  3. Attempts count:                                        │
│      SELECT COUNT(*) FROM attempts                         │
│      WHERE user_id=? AND fact_id IN (domain facts)         │
│  4. Mastered count (for each fact):                        │
│      get_mastery_status(fact_id, user_id)                  │
│        → Last 7 attempts, check 6/7 correct                │
│  Returns: {total_facts, learned_count, attempt_count,      │
│            mastered_count, progress_string, time_spent}    │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ For engagement metrics:
                        ▼
┌────────────────────────────────────────────────────────────┐
│  models.py: Engagement metric functions                    │
│  1. get_questions_answered_today(user_id):                 │
│      SELECT COUNT(*) FROM attempts                         │
│      WHERE user_id=? AND timestamp >= today_start          │
│  2. get_total_time_spent(user_id):                         │
│      SELECT MIN(timestamp), MAX(timestamp)                 │
│      FROM attempts WHERE user_id=?                         │
│      → Calculate delta in minutes                          │
│  3. get_unique_session_count(user_id):                     │
│      SELECT COUNT(DISTINCT session_id)                     │
│      FROM attempts WHERE user_id=?                         │
│  Returns: questions_today, total_time, session_count       │
└───────────────────────┬────────────────────────────────────┘
                        │
                        │ Aggregate all data
                        ▼
┌────────────────────────────────────────────────────────────┐
│  app.py: Render template with context                      │
│  context = {                                               │
│    'student': student,                                     │
│    'assigned_domains': [                                   │
│      {                                                     │
│        'domain': domain,                                   │
│        'progress': progress_data,                          │
│        'time_spent': formatted_time,                       │
│        'attempts': attempt_count                           │
│      },                                                    │
│      ...                                                   │
│    ],                                                      │
│    'questions_today': questions_today,                     │
│    'total_questions': total_questions,                     │
│    'formatted_time': formatted_time,                       │
│    'session_count': session_count                          │
│  }                                                         │
│  render_template('teacher/student_detail.html', **context) │
└────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Token-Based Password Setup (vs. Admin-Set Passwords)

**Decision**: Use secure magic links for password setup instead of admin/teacher setting passwords.

**Rationale:**
- **Security**: No shared passwords, no password transmission over insecure channels
- **Privacy**: Teachers never know student passwords
- **Best practice**: Industry standard (GitHub, Slack, etc. use magic links)
- **User autonomy**: Users set their own secure passwords

**Trade-offs:**
- **Complexity**: Requires token generation, expiration tracking, email integration
- **Email dependency**: Relies on email delivery (mitigated by displaying link if email fails)
- **UX friction**: Extra step for users (mitigated by clear instructions)

**Alternative considered**: Admin/teacher sets initial password, user changes on first login. Rejected due to security concerns (shared passwords, password transmission).

### 2. Organization Schema (Single-Org Currently)

**Decision**: Design multi-tenant schema but implement single organization for v3.0.

**Rationale:**
- **Future-proofing**: Schema supports multiple organizations without migration
- **Simplicity**: Single-org UI is simpler for initial launch
- **Migration path**: Can enable multi-org in future by updating UI only (no schema changes)

**Implementation:**
- All users belong to `organization_id=1` ("Default Organization")
- Teachers can only see students in their organization (filtering already implemented)
- UI assumes single organization (no org switcher, no org selection on account creation)

**Future enhancement**: Add org switcher, allow admin to create organizations, assign teachers to orgs.

### 3. Session-Based Authentication (vs. JWT)

**Decision**: Use Flask-Login session cookies instead of JWT tokens.

**Rationale:**
- **Simplicity**: Flask-Login handles session management automatically
- **Security**: HttpOnly cookies prevent XSS attacks (JWT in localStorage is vulnerable)
- **Stateful**: Server can revoke sessions immediately (logout, deactivation)
- **Standard**: Flask ecosystem best practice

**Trade-offs:**
- **Scalability**: Requires sticky sessions or shared session store for load balancing
- **Mobile apps**: Session cookies less convenient than JWTs (mitigated: this is web-only)

**Alternative considered**: JWT tokens in localStorage. Rejected due to XSS vulnerability and lack of immediate revocation.

### 4. Scrypt Password Hashing (vs. bcrypt/argon2)

**Decision**: Use Werkzeug's scrypt implementation (default).

**Rationale:**
- **Security**: scrypt is PBKDF2-based, resistant to GPU brute-force attacks
- **Built-in**: Werkzeug provides scrypt by default (no extra dependencies)
- **Industry-standard**: Used by Django, Flask, many production systems
- **Auto-salted**: Unique salt per password automatically

**Trade-offs:**
- **Speed**: Slower than bcrypt (intentional - makes brute-force harder)
- **Memory**: Uses more memory than bcrypt (also intentional - prevents GPU attacks)

**Alternatives considered**:
- bcrypt: Faster but less memory-hard (more vulnerable to GPU attacks)
- argon2: Most secure, but requires extra dependency (`argon2-cffi`)

Decision: scrypt is "good enough" and requires no extra dependencies.

### 5. SQLite for Development, PostgreSQL for Production

**Decision**: Use SQLite by default, recommend PostgreSQL for production.

**Rationale:**
- **SQLite (dev)**:
  - Zero configuration (single file, no server)
  - Perfect for development and small deployments
  - Included with Python (no installation)
- **PostgreSQL (prod)**:
  - Concurrent access (SQLite locks entire database on writes)
  - ACID compliance (stronger than SQLite)
  - Advanced features (full-text search, JSON columns, replication)

**Migration path**: SQLAlchemy abstracts database differences - same models/queries work on both.

**Trade-offs**:
- **Complexity**: Users must install and configure PostgreSQL for production
- **Dev/prod parity**: Different databases in dev and prod (rare edge cases)

**Alternative considered**: PostgreSQL everywhere. Rejected due to setup friction for small users.

### 6. Progress Isolation by user_id in Every Query

**Decision**: Require `user_id` parameter in all progress-related functions.

**Rationale:**
- **Security**: Prevents accidental cross-user data leakage
- **Explicitness**: Forces developer to think about which user's data to access
- **Performance**: Enables efficient indexing on `user_id` columns

**Implementation:**
```python
# Before (single-user):
def get_learned_facts(domain_id):
    return FactState.query.filter_by(domain_id=domain_id, learned_at != None).all()

# After (multi-user):
def get_learned_facts(domain_id, user_id):
    return FactState.query.filter_by(
        domain_id=domain_id,
        user_id=user_id,  # Explicit filtering
        learned_at != None
    ).all()
```

**Trade-offs:**
- **Verbosity**: Every function call needs `user_id` parameter
- **Refactoring**: Required updating 50+ function calls during migration

**Alternative considered**: Implicit filtering via context (e.g., thread-local current_user). Rejected due to increased complexity and potential bugs.

### 7. Terminal Aesthetic (vs. Modern UI)

**Decision**: Maintain retro terminal-style green-on-black UI.

**Rationale:**
- **Brand identity**: Distinctive, memorable design
- **Focus**: Minimal distractions for learning
- **Accessibility**: High contrast (green on black) is readable
- **Simplicity**: No JavaScript frameworks, no complex CSS

**Trade-offs:**
- **Design trends**: Not "modern" (but that's intentional)
- **Customization**: Users cannot change theme (future enhancement: theme switcher)

**Alternative considered**: Modern Material Design or Bootstrap. Rejected to maintain project identity.

### 8. Engagement Time as First-to-Last Attempt (vs. Active Time Tracking)

**Decision**: Calculate time spent as delta between first and last attempt timestamp.

**Rationale:**
- **Simplicity**: No client-side tracking, no heartbeat pings, no complex logic
- **Privacy**: No monitoring of user activity beyond quiz attempts
- **Implementation**: Single SQL query (MIN/MAX timestamp)

**Trade-offs:**
- **Accuracy**: Includes breaks, pauses, inactive time (overestimates)
- **Edge cases**: If user leaves tab open, time is inflated

**Alternative considered**: Client-side activity tracking with heartbeat pings every 30 seconds. Rejected due to complexity and privacy concerns.

**Mitigation**: Document that time is an estimate, not actual active time.

---

## Performance Considerations

### Database Indexes

**Critical indexes for fast queries:**

```sql
-- Users table (fast login):
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- User domain assignments (fast domain lookups):
CREATE INDEX idx_uda_user ON user_domain_assignments(user_id);
CREATE INDEX idx_uda_domain ON user_domain_assignments(domain_id);

-- Fact states (fast progress queries):
CREATE INDEX idx_fact_states_user ON fact_states(user_id);
CREATE INDEX idx_fact_states_fact ON fact_states(fact_id);

-- Attempts (fast attempt history):
CREATE INDEX idx_attempts_user ON attempts(user_id);
CREATE INDEX idx_attempts_fact ON attempts(fact_id);
CREATE INDEX idx_attempts_session ON attempts(session_id);
```

**Query optimization examples:**

**Bad (no index, full table scan):**
```sql
SELECT * FROM users WHERE email = 'user@example.com';
-- Without index: O(n) - scans all rows
```

**Good (with index, fast lookup):**
```sql
SELECT * FROM users WHERE email = 'user@example.com';
-- With index: O(log n) - B-tree search
```

### N+1 Query Problem

**Problem**: Loading students with progress causes N queries.

**Bad (N+1 queries):**
```python
students = User.query.filter_by(role='student').all()  # 1 query
for student in students:
    progress = get_student_progress(student.id)  # N queries
    # Total: 1 + N queries
```

**Good (eager loading):**
```python
# Use SQLAlchemy joinedload or subqueryload
students = User.query.options(
    joinedload(User.domain_assignments).joinedload(UserDomainAssignment.domain)
).filter_by(role='student').all()
# Total: 1-2 queries with JOINs
```

**Current implementation**: Acceptable for small numbers of students (<100). For scale, implement eager loading.

### Caching Strategies

**Current**: No caching (acceptable for <1000 users).

**Future enhancements:**

1. **Session-level caching** (memoization):
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def get_mastery_status(fact_id, user_id):
       # Cache mastery calculation within request
       pass
   ```

2. **Application-level caching** (Flask-Caching):
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'simple'})

   @cache.cached(timeout=300, key_prefix='student_progress')
   def get_student_progress(student_id):
       # Cache for 5 minutes
       pass
   ```

3. **Database query caching** (Redis):
   - Cache domain lists (change infrequently)
   - Cache user domain assignments (invalidate on assignment change)

### Scalability Limits

**Current architecture supports:**
- **Users**: ~1,000 concurrent users
- **Domains**: ~50 domains with ~200 facts each
- **Requests**: ~100 requests/second
- **Database size**: ~100 MB for 1,000 users, 10,000 facts, 100,000 attempts

**Bottlenecks at scale:**
1. **SQLite write contention** (>100 concurrent writes/sec)
   - Solution: Migrate to PostgreSQL
2. **Teacher dashboard with 500+ students**
   - Solution: Pagination, lazy loading
3. **Mastery calculation on every attempt**
   - Solution: Cache mastery status, invalidate on new attempt

**Scaling recommendations:**
- <100 users: SQLite is fine
- 100-1,000 users: Migrate to PostgreSQL, add connection pooling
- 1,000-10,000 users: Add application caching (Redis), optimize queries
- >10,000 users: Add read replicas, CDN for static assets, load balancer

---

## Extensibility

### Adding New User Roles

**Current roles**: admin, teacher, student

**To add "parent" role:**

1. **Update User model** (models.py):
   ```python
   # No changes needed - role is string column
   ```

2. **Create parent routes** (app.py):
   ```python
   @app.route("/parent/dashboard")
   @role_required('parent')
   def parent_dashboard():
       # View children's progress
       pass
   ```

3. **Add parent-child relationship**:
   ```python
   class User(db.Model):
       parent_id = db.Column(db.Integer, db.ForeignKey("users.id"))
       children = db.relationship("User", backref="parent")
   ```

4. **Update templates**:
   - Create `templates/parent/dashboard.html`
   - Update `base.html` navigation for parent role

5. **Update role_required decorator** (if needed):
   ```python
   # Already supports multiple roles:
   @role_required('parent', 'admin')
   ```

### Adding New Fact Fields

**Example**: Add "pronunciation" field to facts.

**Process:**

1. **Update JSON file** (facts/example.json):
   ```json
   {
     "domain_name": "Greek Muses",
     "fields": ["name", "domain_of_expertise", "symbol", "pronunciation"],
     "facts": [
       {
         "name": "Calliope",
         "domain_of_expertise": "Epic Poetry",
         "symbol": "Writing Tablet",
         "pronunciation": "kuh-LIE-uh-pee"
       }
     ]
   }
   ```

2. **Reload application**:
   - facts_loader.py automatically reads all fields from JSON
   - No code changes needed

3. **Quiz automatically includes new field**:
   - quiz_logic.py randomly selects from all fields
   - Questions like "What is the pronunciation of Calliope?" generated automatically

**Result**: Fully extensible fact schema with zero code changes.

### Adding New Authentication Providers

**Example**: Add Google OAuth login.

**Implementation:**

1. **Install Flask-Dance**:
   ```bash
   pip install Flask-Dance
   ```

2. **Configure OAuth** (app.py):
   ```python
   from flask_dance.contrib.google import make_google_blueprint
   google_bp = make_google_blueprint(
       client_id="...",
       client_secret="...",
       scope=["email", "profile"]
   )
   app.register_blueprint(google_bp, url_prefix="/login")
   ```

3. **Create OAuth callback** (app.py):
   ```python
   @app.route("/login/google/callback")
   def google_callback():
       google_token = google.token
       resp = google.get("/oauth2/v1/userinfo")
       email = resp.json()["email"]

       # Find or create user
       user = User.query.filter_by(email=email).first()
       if not user:
           # Create new user or reject
           pass

       # Login user
       auth_user = AuthUser(user)
       login_user(auth_user)
       return redirect(role_dashboard_url(user.role))
   ```

4. **Update login template**:
   ```html
   <a href="/login/google">[Login with Google]</a>
   ```

**Result**: OAuth login alongside password-based login.

### Adding REST API

**Example**: Expose progress data via JSON API.

**Implementation:**

1. **Create API blueprint** (api.py):
   ```python
   from flask import Blueprint, jsonify
   api = Blueprint('api', __name__, url_prefix='/api/v1')

   @api.route("/students/<int:student_id>/progress")
   @role_required('teacher', 'admin')
   def api_student_progress(student_id):
       progress = get_student_progress_summary(student_id)
       return jsonify(progress)
   ```

2. **Register blueprint** (app.py):
   ```python
   app.register_blueprint(api)
   ```

3. **Add API authentication**:
   ```python
   # Token-based auth for API:
   from flask_httpauth import HTTPTokenAuth
   auth = HTTPTokenAuth(scheme='Bearer')

   @auth.verify_token
   def verify_token(token):
       # Look up token in database
       pass

   @api.route("/students/<int:student_id>/progress")
   @auth.login_required
   def api_student_progress(student_id):
       pass
   ```

**Result**: RESTful API for mobile apps, integrations, etc.

### Adding Real-Time Features

**Example**: Live progress updates on teacher dashboard.

**Implementation:**

1. **Install Flask-SocketIO**:
   ```bash
   pip install flask-socketio
   ```

2. **Configure SocketIO** (app.py):
   ```python
   from flask_socketio import SocketIO, emit
   socketio = SocketIO(app)

   @socketio.on('subscribe_student')
   def handle_subscribe(data):
       student_id = data['student_id']
       join_room(f'student_{student_id}')
   ```

3. **Emit progress updates** (models.py):
   ```python
   def record_attempt(fact_id, field_name, correct, user_id, session_id):
       # ... existing code ...

       # Emit real-time update
       from flask_socketio import emit
       emit('progress_update', {
           'student_id': user_id,
           'fact_id': fact_id,
           'correct': correct
       }, room=f'student_{user_id}')
   ```

4. **Client-side JavaScript**:
   ```javascript
   const socket = io();
   socket.emit('subscribe_student', {student_id: 42});
   socket.on('progress_update', (data) => {
       // Update UI with new progress
       console.log('Student answered:', data);
   });
   ```

**Result**: Live updates without page refresh.

---

## Conclusion

This architecture balances:
- **Simplicity**: Easy to understand, deploy, and maintain
- **Security**: Industry-standard authentication, authorization, and password handling
- **Scalability**: Supports ~1,000 users out-of-box, scales to 10,000+ with PostgreSQL
- **Extensibility**: Clean separation of concerns, easy to add features
- **Testability**: 162+ tests with >90% coverage

**Design philosophy**: Start simple, scale when needed. Avoid premature optimization. Prioritize clarity over cleverness.
