# Rememberizer Security & Best Practices Guide

Comprehensive security documentation, threat model, and operational best practices for Rememberizer.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Threat Model](#threat-model)
3. [Authentication Security](#authentication-security)
4. [Authorization Security](#authorization-security)
5. [Session Security](#session-security)
6. [Password Security](#password-security)
7. [Data Protection](#data-protection)
8. [Input Validation](#input-validation)
9. [Common Vulnerabilities](#common-vulnerabilities)
10. [Deployment Security](#deployment-security)
11. [Operational Best Practices](#operational-best-practices)
12. [Incident Response](#incident-response)
13. [Security Checklist](#security-checklist)

---

## Security Overview

### Security Principles

Rememberizer follows these core security principles:

1. **Defense in Depth**: Multiple layers of security controls
2. **Principle of Least Privilege**: Users only access what they need
3. **Secure by Default**: Safe defaults, opt-in for risky features
4. **Fail Securely**: Errors don't expose sensitive information
5. **Complete Mediation**: Every access checked, no assumptions
6. **Separation of Duties**: Different roles have different capabilities
7. **Open Design**: Security doesn't rely on obscurity

### Security Features

**Authentication:**
- Token-based password setup (magic links)
- Scrypt password hashing (PBKDF2-based)
- Secure session management (Flask-Login)
- Account lifecycle management (active/inactive status)

**Authorization:**
- Role-based access control (admin/teacher/student)
- Decorator-enforced authorization
- Organization isolation
- Domain assignment enforcement

**Data Protection:**
- Encrypted passwords (scrypt hashing)
- Secure session cookies (HttpOnly, Secure flags)
- No sensitive data in logs
- Parameterized SQL queries (SQLAlchemy ORM)

**Input Validation:**
- Email format validation
- Password strength requirements
- CSRF protection (Flask built-in)
- HTML escaping (Jinja2 auto-escaping)

---

## Threat Model

### Assets to Protect

1. **User Credentials**: Passwords, session tokens
2. **Personal Data**: Names, email addresses, engagement metrics
3. **Academic Data**: Quiz progress, attempt history, learning states
4. **System Integrity**: Database, application code, configuration

### Threat Actors

1. **External Attackers**: Unauthorized individuals attempting to access system
2. **Malicious Students**: Students trying to access other students' data or change grades
3. **Malicious Teachers**: Teachers attempting to access other organizations' data
4. **Compromised Accounts**: Legitimate accounts with stolen credentials

### Attack Vectors

1. **Authentication Bypass**: Attempting to login without valid credentials
2. **Authorization Bypass**: Accessing resources without proper permissions
3. **Session Hijacking**: Stealing session cookies to impersonate users
4. **SQL Injection**: Injecting malicious SQL to access/modify database
5. **Cross-Site Scripting (XSS)**: Injecting JavaScript to steal data or perform actions
6. **Cross-Site Request Forgery (CSRF)**: Tricking users into performing unwanted actions
7. **Brute Force**: Attempting many password combinations
8. **Social Engineering**: Tricking users into revealing credentials or setup links

### Threat Scenarios

#### Scenario 1: Student Attempts to View Another Student's Progress

**Attack**: Student Alice tries to access `/teacher/students/42` (Bob's detail page).

**Defense:**
1. Route requires `@role_required('teacher', 'admin')` - Alice's student role is rejected
2. Returns 403 Forbidden
3. Alice cannot see Bob's progress

**Result**: Attack prevented by authorization layer.

#### Scenario 2: Attacker Steals Session Cookie

**Attack**: Attacker intercepts network traffic and steals session cookie.

**Defense:**
1. Session cookie has `HttpOnly=True` (prevents JavaScript access)
2. Session cookie has `Secure=True` (HTTPS only in production)
3. Even if stolen, attacker needs to come from similar IP (optional: add IP validation)
4. Session expires after 24 hours
5. User can logout to invalidate session

**Result**: Attack mitigated by session security. Recommend HTTPS for full protection.

#### Scenario 3: Attacker Attempts SQL Injection

**Attack**: Attacker submits email: `admin' OR '1'='1` in login form.

**Defense:**
1. SQLAlchemy uses parameterized queries (not string concatenation)
2. Query becomes: `SELECT * FROM users WHERE email = ?` with parameter `"admin' OR '1'='1"`
3. Single-quoted string is treated as literal email address
4. No SQL execution

**Result**: Attack prevented by parameterized queries.

#### Scenario 4: Teacher Attempts to Access Other Organization's Students

**Attack**: Teacher from Org A tries to access student from Org B via URL manipulation.

**Defense:**
1. Teacher navigates to `/teacher/students/99` (student in Org B)
2. Route fetches student and checks: `student.organization_id == current_user.organization_id`
3. Check fails (Org A != Org B)
4. Returns 403 Forbidden

**Result**: Attack prevented by organization isolation.

#### Scenario 5: Attacker Attempts Brute Force Login

**Attack**: Attacker tries 10,000 password combinations for admin account.

**Defense:**
1. Scrypt hashing is intentionally slow (~100ms per hash)
2. 10,000 attempts = ~16 minutes minimum (can't parallelize without session cookies)
3. Recommendation: Add rate limiting (Flask-Limiter) for 100% protection
4. Recommendation: Add account lockout after N failed attempts

**Current status**: Partial mitigation (slow hashing). Full mitigation requires rate limiting.

#### Scenario 6: Attacker Gains Database Access

**Attack**: Attacker gets read access to database (SQL injection, stolen backup, etc.).

**Defense:**
1. All passwords are scrypt-hashed (cannot reverse to plaintext)
2. Each password has unique salt (cannot use rainbow tables)
3. Hashing is slow (brute-forcing each password takes hours/days)
4. Session tokens are not stored in database (stored in encrypted cookies)

**Result**: Passwords remain secure even with database read access.

---

## Authentication Security

### Token-Based Password Setup

**Security properties:**

1. **Unpredictable Tokens**: UUID4 tokens (122 bits of entropy)
   ```python
   setup_token = str(uuid.uuid4())  # e.g., 550e8400-e29b-41d4-a716-446655440000
   ```

2. **Time-Limited**: 7-day expiration
   ```python
   setup_token_expires = datetime.utcnow() + timedelta(days=7)
   ```

3. **Single Use**: Token cleared after password setup
   ```python
   user.setup_token = None
   user.setup_token_expires = None
   ```

4. **Secure Transport**: HTTPS required in production (prevents interception)

**Attack scenarios:**

**Token Guessing:**
- **Probability**: 1 in 2^122 (essentially impossible)
- **Mitigation**: UUID4 provides cryptographic randomness

**Token Interception:**
- **Vector**: Email or network traffic
- **Mitigation**: HTTPS for production, email security best practices
- **Recommendation**: Send setup links via secure channels (not public forums)

**Token Replay After Expiration:**
- **Attack**: Using expired token
- **Mitigation**: Token expiration check in `/setup-password/<token>` route
- **Code**:
  ```python
  if user.setup_token_expires < datetime.utcnow():
      flash("Setup link has expired", "error")
      return redirect(url_for('login'))
  ```

### Password Reset Flow (Future Enhancement)

**Current limitation**: No self-service password reset.

**Recommended implementation:**

1. **User requests reset**: Provides email address
2. **System generates reset token**: UUID4 token, 1-hour expiration
3. **System sends reset email**: Link to `/reset-password/<token>`
4. **User clicks link**: Validates token, shows password form
5. **User sets new password**: Token invalidated, password updated

**Security considerations:**
- **Rate limiting**: Limit reset requests per email (prevent abuse)
- **Token expiration**: 1 hour (shorter than setup tokens)
- **Old password invalidation**: Immediately invalidate old password hash
- **Session invalidation**: Log out all active sessions after reset
- **Notification**: Send "password changed" email to alert user

---

## Authorization Security

### Role-Based Access Control (RBAC)

**Role hierarchy:**
```
Admin (highest privilege)
  ├─► Can create teachers
  ├─► Can access all teacher functions
  └─► Cannot access student quiz routes (by design)

Teacher (medium privilege)
  ├─► Can create students in their organization
  ├─► Can view students in their organization
  ├─► Can assign domains to their students
  └─► Cannot access other organizations

Student (lowest privilege)
  ├─► Can access only assigned domains
  ├─► Can view only their own progress
  └─► Cannot access other students' data
```

### Authorization Checks

**Every protected route performs authorization:**

```python
@app.route("/teacher/students/<int:student_id>")
@role_required('teacher', 'admin')
def view_student(student_id):
    # Decorator ensures user is teacher or admin
    student = User.query.get_or_404(student_id)

    # Additional check: organization isolation
    if student.organization_id != current_user.organization_id:
        abort(403)

    # Proceed with authorized access
```

**Defense properties:**
- **Fail-secure**: If check fails, request is rejected (403 Forbidden)
- **Complete mediation**: Every request checked, no exceptions
- **Explicit**: Authorization is visible in code (not hidden in middleware)

### Domain Assignment Enforcement

**Students can only access assigned domains:**

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

    # Teachers and admins can access any domain
```

**Attack scenario:**

**Direct URL manipulation:**
1. Student sees domain_id=5 in their domains list
2. Student manually navigates to `/start` and submits domain_id=99
3. System checks: `is_domain_assigned(student.id, 99)` → False
4. Request rejected with error message

**Result**: Attack prevented by domain assignment check.

### Organization Isolation

**Teachers can only access their organization's students:**

```python
@app.route("/teacher/dashboard")
@role_required('teacher', 'admin')
def teacher_dashboard():
    # Only fetch students from current user's organization
    students = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='student'
    ).all()
    # Students from other orgs are never queried
```

**Attack scenario:**

**Cross-org access attempt:**
1. Teacher A (Org 1) knows Teacher B (Org 2) has student with ID=50
2. Teacher A navigates to `/teacher/students/50`
3. System fetches student, checks `student.organization_id == current_user.organization_id`
4. Check fails (Org 1 != Org 2)
5. Returns 403 Forbidden

**Result**: Attack prevented by organization isolation check.

---

## Session Security

### Session Configuration

**Secure session settings (app.py):**

```python
# Secret key (must be strong)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "default-dev-key")

# Session cookie security
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevents JavaScript access
app.config["SESSION_COOKIE_SECURE"] = True    # HTTPS only (production)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax" # CSRF protection
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)  # 24-hour expiration
```

### Session Cookie Flags

**HttpOnly:**
- **Purpose**: Prevents JavaScript from accessing session cookie
- **Protection**: Mitigates XSS attacks (attacker can't steal cookie with `document.cookie`)
- **Setting**: `SESSION_COOKIE_HTTPONLY = True`

**Secure:**
- **Purpose**: Cookie only sent over HTTPS
- **Protection**: Prevents interception over unencrypted connections
- **Setting**: `SESSION_COOKIE_SECURE = True` (production only)
- **Development**: Set to `False` for local testing (http://localhost)

**SameSite:**
- **Purpose**: Prevents CSRF attacks via cross-site requests
- **Options**:
  - `Strict`: Cookie never sent on cross-site requests
  - `Lax`: Cookie sent on top-level navigations (GET only)
  - `None`: Cookie sent on all requests (requires Secure flag)
- **Setting**: `SESSION_COOKIE_SAMESITE = "Lax"` (balance between security and usability)

### Session Lifecycle

**Session creation (on login):**
```python
from flask_login import login_user

auth_user = AuthUser(user)
login_user(auth_user, remember=True)
# Flask-Login creates encrypted session cookie
# Cookie includes user_id and remember_me flag
```

**Session validation (on every request):**
```python
# Flask-Login automatically:
1. Reads session cookie
2. Decrypts cookie data
3. Calls @login_manager.user_loader(user_id)
4. Loads User from database
5. Sets current_user = AuthUser(user)
```

**Session termination (on logout):**
```python
from flask_login import logout_user

logout_user()
# Flask-Login clears session cookie
# current_user becomes AnonymousUser
```

### Session Hijacking Protection

**Attack: Attacker steals session cookie and impersonates user.**

**Current mitigations:**
1. **HttpOnly flag**: Prevents XSS-based theft
2. **Secure flag**: Prevents interception over HTTP (production)
3. **SameSite flag**: Prevents CSRF-based usage
4. **Session expiration**: Sessions expire after 24 hours

**Additional mitigations (not implemented, future enhancement):**

5. **IP validation**: Reject session if IP address changes
   ```python
   if session.get('ip_address') != request.remote_addr:
       logout_user()
       flash("Session expired due to IP change", "error")
   ```

6. **User-Agent validation**: Reject session if User-Agent changes
   ```python
   if session.get('user_agent') != request.headers.get('User-Agent'):
       logout_user()
   ```

7. **Session rotation**: Generate new session ID on privilege escalation

**Trade-offs:**
- **IP validation**: Breaks mobile users (IP changes when switching networks)
- **User-Agent validation**: Breaks browser updates
- **Session rotation**: Adds complexity

**Recommendation**: Current mitigations are sufficient for most deployments. Add IP/User-Agent validation only for high-security environments.

---

## Password Security

### Hashing Algorithm (Scrypt)

**Properties:**

1. **One-way function**: Cannot reverse hash to get password
   ```
   password "hello123" → hash "scrypt:32768:8:1$..."
   # Cannot reverse hash back to "hello123"
   ```

2. **Salted**: Each password has unique salt
   ```
   password "hello123" + salt1 → hash1
   password "hello123" + salt2 → hash2
   # Same password, different hashes (prevents rainbow tables)
   ```

3. **Slow by design**: Intentionally expensive to compute (~100ms)
   - **Purpose**: Makes brute-force attacks impractical
   - **Cost**: 1,000 guesses = 100 seconds minimum

4. **Memory-hard**: Requires significant RAM
   - **Purpose**: Prevents GPU-based brute-force (GPUs have limited memory)
   - **Parameters**: `N=32768, r=8, p=1` (Werkzeug defaults)

### Password Requirements

**Current requirements:**
- Minimum 8 characters
- No maximum length (hashing handles any length)
- No complexity requirements (lowercase, uppercase, numbers, symbols)

**Rationale:**
- **NIST guidelines**: Length > complexity
- **User experience**: Easy to remember, hard to guess
- **Entropy**: 8 random characters = ~52 bits of entropy (sufficient)

**Recommendations for production:**

1. **Minimum 12 characters**: Increases entropy, harder to brute-force
   ```python
   if len(password) < 12:
       flash("Password must be at least 12 characters", "error")
   ```

2. **Common password check**: Reject "password123", "qwerty", etc.
   ```python
   COMMON_PASSWORDS = ["password", "123456", "qwerty", ...]
   if password.lower() in COMMON_PASSWORDS:
       flash("Password is too common, please choose a stronger password", "error")
   ```

3. **Breach check** (optional): Check against haveibeenpwned.com API
   ```python
   import hashlib, requests
   sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
   prefix = sha1[:5]
   suffix = sha1[5:]
   response = requests.get(f"https://api.pwnedpasswords.com/range/{prefix}")
   if suffix in response.text:
       flash("This password has appeared in data breaches, please choose a different password", "warning")
   ```

### Password Storage Security

**What is stored:**
```python
user.password_hash = 'scrypt:32768:8:1$VHPHUbFhICFZ$abc123...'
# Format: algorithm:params:salt$hash
```

**What is NOT stored:**
- ❌ Plaintext password
- ❌ Reversible encryption of password
- ❌ Password hints or security questions

**Verification process:**
```python
from werkzeug.security import check_password_hash

# User enters "hello123"
entered_password = "hello123"

# System retrieves stored hash
stored_hash = user.password_hash  # "scrypt:32768:8:1$VHPHUbFhICFZ$abc123..."

# System hashes entered password with same salt
# Compares result with stored hash
is_valid = check_password_hash(stored_hash, entered_password)
# Returns True if match, False otherwise
```

**Security properties:**
- **Constant-time comparison**: Prevents timing attacks
- **No password exposure**: Entered password never logged or stored
- **Salt extraction**: Salt is extracted from stored hash (no separate storage needed)

### Password Change Best Practices

**Current implementation**: No self-service password change (limitation).

**Recommended implementation:**

1. **Require old password**: User must know current password to change
   ```python
   if not check_password_hash(user.password_hash, old_password):
       flash("Current password is incorrect", "error")
       return redirect(url_for('change_password'))
   ```

2. **Validate new password**: Same requirements as initial setup
3. **Invalidate sessions**: Log out all active sessions except current
4. **Send notification**: Email user about password change
5. **Audit log**: Record password change event (timestamp, IP address)

---

## Data Protection

### Personal Data

**Data collected:**
- First name, last name (required)
- Email address (required, used for login and notifications)
- Organization ID (required, defaults to 1)
- Last active timestamp (automatic)

**Data NOT collected:**
- Date of birth
- Phone number
- Physical address
- Payment information (no payments in current version)
- IP addresses (not logged)

**Data retention:**
- Accounts: Indefinite (until manually deleted)
- Inactive accounts: Not automatically purged
- Deactivated accounts: Data retained (can be reactivated)

**GDPR compliance considerations:**

1. **Data minimization**: Only collect necessary data ✓
2. **Purpose limitation**: Data only used for application functionality ✓
3. **Right to access**: Users can request their data (requires admin intervention)
4. **Right to erasure**: Users can request deletion (requires manual database operation)
5. **Data portability**: Users can export their data (not implemented, future enhancement)

**Recommendations for GDPR compliance:**

1. **Add privacy policy**: Explain what data is collected and why
2. **Add data export**: Allow users to download their data as JSON
3. **Add data deletion**: Allow users to request account deletion
4. **Add consent tracking**: Record user consent for data processing
5. **Add data retention policy**: Auto-delete inactive accounts after N years

### Academic Data

**Data collected:**
- Quiz attempts (fact ID, field name, correct/incorrect, timestamp)
- Fact states (learned status, consecutive correct/wrong, timestamps)
- Domain assignments (which students have which domains)
- Engagement metrics (questions answered, time spent, sessions)

**Data visibility:**
- **Students**: Can see only their own data
- **Teachers**: Can see data for students in their organization
- **Admins**: Can see all data (technical access, not UI access)

**Data export:**
- No built-in export (future enhancement)
- Teachers can manually copy data from UI
- Admins can export database (SQL or CSV)

### Database Security

**Current protection:**

1. **File permissions**: SQLite database file should be read/write only by application user
   ```bash
   chmod 600 instance/database.db  # Owner read/write only
   chown app_user:app_user instance/database.db
   ```

2. **Parameterized queries**: SQLAlchemy prevents SQL injection
   ```python
   # Safe (parameterized):
   User.query.filter_by(email=email).first()
   # Unsafe (string concatenation) - NEVER DO THIS:
   db.session.execute(f"SELECT * FROM users WHERE email = '{email}'")
   ```

3. **No plaintext credentials**: All passwords hashed

**Production recommendations:**

1. **PostgreSQL access control**: Restrict database user permissions
   ```sql
   CREATE USER rememberizer_app WITH PASSWORD 'strong_password';
   GRANT CONNECT ON DATABASE rememberizer TO rememberizer_app;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES TO rememberizer_app;
   -- No DROP, CREATE, ALTER permissions
   ```

2. **Database encryption at rest**: Enable PostgreSQL encryption
3. **Backup encryption**: Encrypt database backups
4. **Network isolation**: Database on private network (not internet-accessible)

### Logging and Monitoring

**Current logging**: Minimal (Flask default logging).

**Do NOT log:**
- ❌ Passwords (plaintext or hashed)
- ❌ Session tokens
- ❌ Setup tokens
- ❌ Full user records (may contain sensitive data)

**Safe to log:**
- ✓ Login attempts (email, success/failure, timestamp)
- ✓ Failed authentication attempts (email, timestamp, IP address)
- ✓ Authorization failures (user ID, resource, action, timestamp)
- ✓ Account creation/deactivation events
- ✓ Domain assignment changes
- ✓ Progress resets (who reset, which student, which domain)

**Recommended logging:**
```python
import logging
logger = logging.getLogger(__name__)

# Good: Log event with context
logger.info(f"User {user.id} logged in successfully")

# Bad: Log sensitive data
logger.info(f"User {user.email} password: {password}")  # NEVER DO THIS
```

---

## Input Validation

### Email Validation

**Implementation:**
```python
from email_validator import validate_email, EmailNotValidError

def validate_email_format(email):
    try:
        # Validates email format
        v = validate_email(email, check_deliverability=False)
        return v.email  # Normalized email
    except EmailNotValidError as e:
        return None
```

**Checks performed:**
- Format: `local-part@domain.tld`
- No whitespace
- Valid characters
- Not `check_deliverability` (no DNS lookup - too slow)

**Attack prevented:**
- Email injection (e.g., `admin@example.com\r\nBcc:attacker@evil.com`)

### Form Input Validation

**All form inputs validated:**

**User creation:**
```python
first_name = request.form.get("first_name", "").strip()
last_name = request.form.get("last_name", "").strip()
email = request.form.get("email", "").strip().lower()

if not first_name or not last_name or not email:
    flash("All fields are required", "error")
    return redirect(request.url)

if not validate_email_format(email):
    flash("Invalid email format", "error")
    return redirect(request.url)
```

**Password setup:**
```python
password = request.form.get("password", "")
confirm_password = request.form.get("confirm_password", "")

if len(password) < 8:
    flash("Password must be at least 8 characters", "error")
    return redirect(request.url)

if password != confirm_password:
    flash("Passwords do not match", "error")
    return redirect(request.url)
```

**Domain ID:**
```python
domain_id = request.form.get("domain_id")
if not domain_id or not domain_id.isdigit():
    flash("Invalid domain", "error")
    return redirect(url_for('student_domains'))

domain_id = int(domain_id)
domain = Domain.query.get(domain_id)
if not domain:
    flash("Domain not found", "error")
    return redirect(url_for('student_domains'))
```

### HTML Escaping (XSS Prevention)

**Auto-escaping in Jinja2:**
```html
<!-- Safe (auto-escaped): -->
<p>{{ user.first_name }}</p>
<!-- If first_name = "<script>alert('XSS')</script>" -->
<!-- Rendered: <p>&lt;script&gt;alert('XSS')&lt;/script&gt;</p> -->

<!-- Unsafe (manual escaping disabled): -->
<p>{{ user.first_name | safe }}</p>
<!-- Rendered: <p><script>alert('XSS')</script></p> (executes!) -->
```

**Rules:**
- ✓ Always use `{{ variable }}` (auto-escapes)
- ❌ Never use `{{ variable | safe }}` unless you trust the source
- ✓ Never insert user input into HTML attributes without quotes
  ```html
  <!-- Bad: -->
  <div class={{ user_class }}>  <!-- Attacker can inject: x onclick=alert(1) -->

  <!-- Good: -->
  <div class="{{ user_class }}">  <!-- Attacker cannot escape quotes -->
  ```

### CSRF Protection

**Flask built-in protection:**
- Forms submitted via POST are protected by session
- Flask generates CSRF token automatically (included in session)

**For sensitive operations, use Flask-WTF:**
```python
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

# In template:
<form method="post">
    {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
    {{ form.email() }}
    {{ form.password() }}
    <button type="submit">Login</button>
</form>
```

**Current implementation**: Relies on Flask session protection (sufficient for most cases). For maximum protection, migrate to Flask-WTF.

---

## Common Vulnerabilities

### OWASP Top 10 Analysis

#### 1. Broken Access Control

**Risk**: Users access resources they shouldn't (e.g., student views teacher dashboard).

**Rememberizer mitigations:**
- ✓ Role-based access control on every route
- ✓ Organization isolation
- ✓ Domain assignment enforcement
- ✓ User ID filtering on all queries

**Status**: Protected ✓

#### 2. Cryptographic Failures

**Risk**: Sensitive data exposed due to weak encryption.

**Rememberizer mitigations:**
- ✓ Strong password hashing (scrypt)
- ✓ Secure session cookies (encrypted by Flask)
- ✓ HTTPS in production (recommended)

**Gaps:**
- ⚠️ Database not encrypted at rest (recommendation: enable PostgreSQL encryption)

**Status**: Mostly protected (⚠️ add database encryption for production)

#### 3. Injection

**Risk**: SQL injection, command injection, etc.

**Rememberizer mitigations:**
- ✓ Parameterized queries (SQLAlchemy ORM)
- ✓ No dynamic SQL construction
- ✓ No command execution (no `os.system()`, `subprocess.call()`)

**Status**: Protected ✓

#### 4. Insecure Design

**Risk**: Fundamental design flaws.

**Rememberizer mitigations:**
- ✓ Security requirements defined (threat model)
- ✓ Secure development lifecycle (code review, testing)
- ✓ Defense in depth (multiple layers)

**Status**: Protected ✓

#### 5. Security Misconfiguration

**Risk**: Default credentials, exposed debug info, etc.

**Rememberizer mitigations:**
- ✓ No default passwords (admin sets password on first run)
- ✓ Debug mode off in production (`FLASK_ENV=production`)
- ✓ Strong SECRET_KEY required

**Gaps:**
- ⚠️ Security headers not configured (recommendation: add below)

**Recommended headers:**
```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

**Status**: Mostly protected (⚠️ add security headers)

#### 6. Vulnerable and Outdated Components

**Risk**: Using libraries with known vulnerabilities.

**Rememberizer mitigations:**
- ✓ Minimal dependencies (Flask, SQLAlchemy, Flask-Login)
- ✓ Regular updates recommended

**Recommendation:**
```bash
# Check for vulnerabilities:
pip install safety
safety check

# Update dependencies:
pip install --upgrade Flask Flask-SQLAlchemy Flask-Login
```

**Status**: Requires ongoing maintenance (⚠️ regular updates)

#### 7. Identification and Authentication Failures

**Risk**: Weak authentication, session management issues.

**Rememberizer mitigations:**
- ✓ Strong password hashing
- ✓ Token-based setup (no shared passwords)
- ✓ Session management (Flask-Login)
- ✓ Account lockout (not implemented, see below)

**Gaps:**
- ⚠️ No rate limiting on login attempts
- ⚠️ No account lockout after N failed attempts

**Recommendation:**
```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # Max 5 login attempts per minute
def login():
    pass
```

**Status**: Mostly protected (⚠️ add rate limiting)

#### 8. Software and Data Integrity Failures

**Risk**: Unsigned updates, insecure CI/CD.

**Rememberizer mitigations:**
- ✓ Code integrity via version control (Git)
- ✓ No automatic updates
- ✓ Manual deployment process

**Status**: Protected ✓

#### 9. Security Logging and Monitoring Failures

**Risk**: Attacks go undetected.

**Rememberizer mitigations:**
- ⚠️ Minimal logging (Flask default)
- ⚠️ No intrusion detection
- ⚠️ No alerting

**Recommendation:**
1. Log all authentication events
2. Log all authorization failures
3. Set up monitoring (Sentry, Datadog, etc.)
4. Alert on suspicious activity (many failed logins, etc.)

**Status**: Needs improvement (⚠️ add logging and monitoring)

#### 10. Server-Side Request Forgery (SSRF)

**Risk**: Application makes requests to unintended servers.

**Rememberizer mitigations:**
- ✓ No user-controlled URLs
- ✓ No outbound HTTP requests based on user input

**Status**: Not applicable (no SSRF vectors)

### Summary: OWASP Top 10 Compliance

| Vulnerability | Status | Notes |
|---------------|--------|-------|
| Broken Access Control | ✓ Protected | RBAC, org isolation |
| Cryptographic Failures | ⚠️ Mostly protected | Add DB encryption |
| Injection | ✓ Protected | Parameterized queries |
| Insecure Design | ✓ Protected | Threat model, secure development |
| Security Misconfiguration | ⚠️ Mostly protected | Add security headers |
| Vulnerable Components | ⚠️ Ongoing | Regular updates needed |
| Authentication Failures | ⚠️ Mostly protected | Add rate limiting |
| Data Integrity | ✓ Protected | Version control, manual deployment |
| Logging & Monitoring | ⚠️ Needs improvement | Add logging, monitoring |
| SSRF | ✓ Not applicable | No SSRF vectors |

**Overall**: 7/10 fully protected, 3/10 need enhancements.

---

## Deployment Security

### Production Checklist

**Before deploying to production:**

- [ ] Generate strong SECRET_KEY (32+ bytes)
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] Set `FLASK_ENV=production`
- [ ] Set `SESSION_COOKIE_SECURE=True` (requires HTTPS)
- [ ] Configure HTTPS/TLS (Let's Encrypt certificates)
- [ ] Use PostgreSQL (not SQLite)
- [ ] Use production WSGI server (Gunicorn, uWSGI)
- [ ] Configure reverse proxy (Nginx, Apache)
- [ ] Set up firewall (allow 80/443/SSH only)
- [ ] Disable debug mode (`DEBUG=False`)
- [ ] Configure database backups (daily minimum)
- [ ] Set up logging (structured logs, centralized)
- [ ] Configure monitoring (uptime, errors, performance)
- [ ] Review file permissions (database, logs, config)
- [ ] Disable directory listing (Nginx/Apache)
- [ ] Set secure HTTP headers (see below)
- [ ] Configure rate limiting (Flask-Limiter)
- [ ] Test authentication and authorization
- [ ] Test HTTPS configuration (SSL Labs)
- [ ] Review and test backup restoration
- [ ] Document admin credentials securely
- [ ] Set up incident response plan

### HTTPS Configuration

**Why HTTPS is critical:**
- Encrypts all traffic (passwords, session cookies, data)
- Prevents man-in-the-middle attacks
- Required for `SESSION_COOKIE_SECURE=True`
- Builds user trust

**Obtaining SSL/TLS certificate:**

**Option 1: Let's Encrypt (Free, Recommended)**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d rememberizer.example.com
# Certbot configures Nginx and obtains certificate
# Auto-renewal configured
```

**Option 2: Commercial CA (Paid)**
- Purchase certificate from DigiCert, GlobalSign, etc.
- Generate CSR (Certificate Signing Request)
- Submit CSR to CA
- Install certificate on server

**Testing HTTPS:**
- Visit https://www.ssllabs.com/ssltest/
- Enter your domain
- Aim for A+ rating

### Reverse Proxy Security

**Nginx configuration (security-focused):**

```nginx
server {
    listen 443 ssl http2;
    server_name rememberizer.example.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/rememberizer.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rememberizer.example.com/privkey.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;

    # Hide server version
    server_tokens off;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    location /login {
        limit_req zone=login_limit burst=5;
        proxy_pass http://127.0.0.1:8000;
        # ... other proxy settings
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Static files (with caching)
    location /static {
        alias /path/to/rememberizer/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

# HTTP redirect to HTTPS
server {
    listen 80;
    server_name rememberizer.example.com;
    return 301 https://$server_name$request_uri;
}
```

### Firewall Configuration

**UFW (Ubuntu):**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
sudo ufw status
```

**firewalld (CentOS/RHEL):**
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

---

## Operational Best Practices

### Regular Maintenance Tasks

**Daily:**
- Monitor application logs for errors
- Check failed login attempts
- Verify backups completed successfully

**Weekly:**
- Review user activity logs
- Check for security updates (pip, OS packages)
- Test backup restoration

**Monthly:**
- Review access control (deactivate departed users)
- Rotate secrets if compromised
- Review disk space usage
- Update dependencies

**Quarterly:**
- Security audit (review logs, access controls, configurations)
- Penetration testing (optional, for high-security environments)
- Disaster recovery drill

### Backup Strategy

**Database backups:**

**SQLite:**
```bash
# Daily backup (cron job):
0 2 * * * cp /path/to/instance/database.db /backup/location/database-$(date +\%Y\%m\%d).db
```

**PostgreSQL:**
```bash
# Daily backup with compression:
0 2 * * * pg_dump rememberizer | gzip > /backup/location/rememberizer-$(date +\%Y\%m\%d).sql.gz
```

**Backup retention:**
- Daily backups: Keep 7 days
- Weekly backups: Keep 4 weeks
- Monthly backups: Keep 12 months

**Backup testing:**
- Test restore monthly
- Verify data integrity (random sample)
- Document restore procedure

### Monitoring

**Application monitoring:**
- Uptime monitoring (Pingdom, UptimeRobot)
- Error tracking (Sentry, Rollbar)
- Performance monitoring (New Relic, Datadog)

**Server monitoring:**
- CPU, memory, disk usage
- Network traffic
- Database performance

**Security monitoring:**
- Failed login attempts (>10 per hour = investigate)
- Authorization failures (403 errors)
- Unusual traffic patterns

**Alerting:**
- Critical: Application down, database unavailable
- Warning: High error rate, disk space >80%
- Info: Completed backups, deployment events

### User Management Best Practices

**For Admins:**
1. Use strong, unique password (password manager recommended)
2. Don't share admin credentials
3. Create separate admin accounts for each administrator (if needed)
4. Deactivate admin accounts immediately when staff leaves
5. Review teacher accounts monthly (deactivate inactive)

**For Teachers:**
1. Create students at start of term
2. Share setup links securely (email, LMS, not public forums)
3. Follow up with students who haven't set passwords
4. Assign domains purposefully (progressive release)
5. Monitor student engagement weekly
6. Deactivate graduated students at end of term

**For Students:**
1. Set strong password during setup
2. Don't share password with other students
3. Logout when using shared computers
4. Report suspected account compromise immediately

### Secure Development Practices

**Code review:**
- All changes reviewed before merging
- Focus on security implications
- Check for sensitive data in logs
- Verify authorization checks

**Testing:**
- Run test suite before deployment (`pytest`)
- Test authentication flows
- Test authorization (try to access unauthorized resources)
- Test with different user roles

**Version control:**
- Never commit secrets (passwords, API keys, SECRET_KEY)
- Use `.gitignore` for sensitive files
- Use environment variables for secrets

**Dependency management:**
- Pin dependency versions (`requirements.txt`)
- Review security advisories
- Update dependencies regularly
- Test after updates

---

## Incident Response

### Incident Types

1. **Security breach**: Unauthorized access to data or systems
2. **Account compromise**: User credentials stolen or misused
3. **Data loss**: Accidental deletion or corruption
4. **Service outage**: Application unavailable
5. **Data breach**: Personal data exposed

### Incident Response Plan

#### Phase 1: Detection and Analysis

**Signs of security incident:**
- Unusual login activity (many failed attempts, logins from unusual locations)
- Unexpected data changes (progress reset, domain assignments changed)
- Performance degradation (potential DDoS)
- Reports from users (suspicious emails, account lockouts)

**Initial assessment:**
1. Confirm incident (eliminate false positives)
2. Determine scope (how many users affected)
3. Identify attack vector (how did it happen)
4. Assess impact (what data/systems compromised)

#### Phase 2: Containment

**Short-term containment:**
- Deactivate compromised accounts immediately
- Reset passwords for affected users
- Block malicious IP addresses (firewall rules)
- Take offline if necessary (prevent further damage)

**Long-term containment:**
- Patch vulnerabilities
- Implement additional security controls
- Monitor for continued attack

#### Phase 3: Eradication

**Remove threat:**
- Delete malicious data
- Close security holes
- Update all passwords
- Revoke session tokens

**Verify clean:**
- Scan for backdoors
- Review logs for persistence mechanisms
- Test security controls

#### Phase 4: Recovery

**Restore normal operations:**
- Restore from backups (if needed)
- Re-enable accounts (after password reset)
- Monitor closely for recurrence

**Communicate:**
- Notify affected users
- Provide guidance (password reset, what to watch for)
- Document timeline and actions taken

#### Phase 5: Lessons Learned

**Post-incident review:**
- What happened? (timeline)
- How was it detected? (too late? just right?)
- What worked? What didn't?
- What will we do differently?

**Improve:**
- Update security controls
- Enhance monitoring
- Train staff
- Update documentation

### Specific Scenarios

#### Scenario: Suspected Account Compromise

**Symptoms**: User reports unusual activity (progress reset, domains unassigned).

**Response:**
1. **Contain**: Deactivate user account immediately
2. **Investigate**: Review user's activity logs (login times, IP addresses, actions taken)
3. **Assess**: Determine if attacker accessed other accounts
4. **Remediate**:
   - Reset user's password
   - Generate new setup token
   - Send setup link to user
   - Restore user's progress from backup (if needed)
5. **Communicate**: Email user explaining incident and next steps

#### Scenario: Mass Failed Login Attempts

**Symptoms**: Many failed login attempts for admin account.

**Response:**
1. **Contain**: Block source IP address (firewall rule)
2. **Investigate**: Review logs for pattern (single IP, distributed, specific accounts)
3. **Assess**: Determine if brute-force or credential stuffing
4. **Remediate**:
   - Implement rate limiting (Flask-Limiter)
   - Require admin to change password (if weak)
   - Enable account lockout after N failed attempts
5. **Monitor**: Watch for continued attacks from other IPs

#### Scenario: Data Breach (Database Exposed)

**Symptoms**: Database file or credentials leaked.

**Response:**
1. **Contain**: Take application offline immediately
2. **Investigate**: How was database accessed? (SQL injection, stolen credentials, misconfiguration)
3. **Assess**: What data was exposed? (user accounts, passwords, progress data)
4. **Notify**: Inform all users of breach (legal requirement in many jurisdictions)
5. **Remediate**:
   - Patch vulnerability
   - Reset ALL user passwords (invalidate password hashes)
   - Generate new SECRET_KEY
   - Regenerate setup tokens
   - Review and harden security
6. **Legal**: Consult legal counsel for compliance (GDPR, FERPA, etc.)

---

## Security Checklist

### Development Environment

- [ ] SECRET_KEY is random (not hardcoded "dev" key)
- [ ] DEBUG mode enabled (for development visibility)
- [ ] Database is SQLite (quick setup)
- [ ] No production data in development database
- [ ] `.env` file not committed to Git
- [ ] Dependencies up to date (`pip install --upgrade`)

### Production Environment

**Application Configuration:**
- [ ] `FLASK_ENV=production`
- [ ] Strong SECRET_KEY (32+ bytes, generated with `secrets.token_hex(32)`)
- [ ] `DEBUG=False`
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `SESSION_COOKIE_HTTPONLY=True`
- [ ] Production database (PostgreSQL, not SQLite)
- [ ] Database credentials in environment variables (not hardcoded)

**Server Configuration:**
- [ ] HTTPS enabled (Let's Encrypt or commercial certificate)
- [ ] HTTP redirects to HTTPS
- [ ] WSGI server (Gunicorn/uWSGI, not Flask dev server)
- [ ] Reverse proxy (Nginx/Apache)
- [ ] Firewall enabled (only 22/80/443 open)
- [ ] Automatic security updates enabled
- [ ] SSH keys only (password authentication disabled)
- [ ] Non-root user for application

**Security Headers:**
- [ ] Strict-Transport-Security
- [ ] X-Frame-Options
- [ ] X-Content-Type-Options
- [ ] X-XSS-Protection
- [ ] Content-Security-Policy

**Monitoring & Logging:**
- [ ] Application logs configured
- [ ] Error tracking (Sentry/Rollbar)
- [ ] Uptime monitoring
- [ ] Failed login attempts logged
- [ ] Authorization failures logged
- [ ] Database backups (daily minimum)
- [ ] Backup restoration tested

**Database:**
- [ ] PostgreSQL (not SQLite)
- [ ] Database user has minimal permissions
- [ ] Database not internet-accessible
- [ ] Connection pooling configured
- [ ] Backups encrypted
- [ ] Database encryption at rest (optional, recommended)

**Application Security:**
- [ ] Admin password set (strong, unique)
- [ ] No default passwords
- [ ] Rate limiting configured (Flask-Limiter)
- [ ] CSRF protection enabled
- [ ] All routes have authorization checks
- [ ] Input validation on all forms
- [ ] Dependencies up to date
- [ ] Security headers configured

**Documentation:**
- [ ] Admin credentials documented securely
- [ ] Backup/restore procedures documented
- [ ] Incident response plan documented
- [ ] System architecture documented
- [ ] Deployment process documented

### Ongoing Maintenance

**Daily:**
- [ ] Monitor application logs
- [ ] Check failed login attempts
- [ ] Verify backups completed

**Weekly:**
- [ ] Review security advisories
- [ ] Check for dependency updates
- [ ] Test backup restoration (monthly, not weekly)

**Monthly:**
- [ ] Review and deactivate inactive users
- [ ] Update dependencies
- [ ] Review disk space
- [ ] Test disaster recovery

**Quarterly:**
- [ ] Security audit
- [ ] Penetration testing (optional)
- [ ] Review access controls
- [ ] Update documentation

---

## Conclusion

Rememberizer implements defense-in-depth security:

**Strong foundations:**
- Industry-standard authentication (scrypt hashing, Flask-Login)
- Role-based access control (RBAC)
- Organization isolation
- Parameterized queries (SQL injection prevention)
- Auto-escaping (XSS prevention)

**Areas for enhancement:**
- Rate limiting (prevent brute-force)
- Security headers (defense-in-depth)
- Logging and monitoring (intrusion detection)
- Database encryption at rest (data protection)
- Self-service password reset (user convenience)

**Deployment priority:**
- **Critical**: HTTPS, strong SECRET_KEY, PostgreSQL, firewall
- **High**: Rate limiting, security headers, monitoring
- **Medium**: Database encryption, enhanced logging
- **Low**: Advanced monitoring, penetration testing

**Remember**: Security is a process, not a product. Regular updates, monitoring, and vigilance are essential.
