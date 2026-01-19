# Rememberizer Installation & Deployment Guide

Complete guide for installing, configuring, and deploying Rememberizer in development and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Installation](#development-installation)
3. [Database Setup](#database-setup)
4. [First-Time Admin Setup](#first-time-admin-setup)
5. [Configuration](#configuration)
6. [Production Deployment](#production-deployment)
7. [Email Configuration](#email-configuration)
8. [Database Migrations](#database-migrations)
9. [Troubleshooting](#troubleshooting)
10. [Backup and Recovery](#backup-and-recovery)

## Prerequisites

### Required Software

- **Python**: Version 3.8 or higher
- **pip**: Python package installer (usually included with Python)
- **Git**: For cloning the repository
- **Web Browser**: Any modern browser (Chrome, Firefox, Safari, Edge)

### Recommended for Production

- **PostgreSQL**: For production database (SQLite is default for development)
- **Nginx or Apache**: Reverse proxy server
- **Gunicorn or uWSGI**: Production WSGI server
- **Supervisor or systemd**: Process management
- **SSL/TLS Certificate**: For HTTPS (Let's Encrypt recommended)

### System Requirements

**Minimum:**
- 512 MB RAM
- 1 GB disk space
- Single-core CPU

**Recommended:**
- 2 GB RAM
- 5 GB disk space
- Dual-core CPU

**Tested Platforms:**
- Windows 10/11
- Ubuntu 20.04/22.04 LTS
- macOS 11+
- Debian 10+
- CentOS 8+

## Development Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd rememberizer
```

Or download and extract the ZIP archive.

### Step 2: Create Virtual Environment (Recommended)

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

Your prompt should now show `(venv)` prefix.

### Step 3: Install Dependencies

**Required dependencies:**
```bash
pip install -r requirements.txt
```

This installs:
- Flask 2.3+
- Flask-SQLAlchemy 3.0+
- Flask-Login 0.6+
- Werkzeug 2.3+
- email-validator 2.1+

**Development dependencies (optional):**
```bash
pip install -r requirements-dev.txt
```

This additionally installs:
- pytest 7.4+
- pytest-flask 1.2+
- pytest-cov 4.1+
- black 23.0+
- flake8 6.0+

### Step 4: Verify Installation

```bash
python --version        # Should be 3.8+
pip list                # Should show Flask, SQLAlchemy, etc.
```

### Step 5: Initialize Database (Optional)

The database initializes automatically on first request, but you can manually initialize:

```bash
python init_database.py
```

Expected output:
```
Database initialized successfully!
Tables created:
- organizations
- users
- user_domain_assignments
- domains
- facts
- fact_states
- attempts
```

### Step 6: Start Development Server

```bash
python app.py
```

Expected output:
```
No admin account found. Create one now? [Y/n] Y
Enter admin email: admin@example.com
Enter admin password (min 8 chars): ********
Admin account created successfully!
Admin Email: admin@example.com

 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

Navigate to `http://localhost:5000` in your browser.

## Database Setup

### SQLite (Default for Development)

**Location**: `instance/database.db`

**Automatic Setup**: Database file is created automatically on first request.

**Manual Setup**:
```bash
python init_database.py
```

**View Database**:
```bash
sqlite3 instance/database.db
sqlite> .tables
sqlite> .schema users
sqlite> SELECT * FROM users;
sqlite> .quit
```

**Delete and Recreate**:
```bash
# Windows
del instance\database.db

# Linux/macOS
rm instance/database.db

# Restart app to recreate
python app.py
```

### PostgreSQL (Recommended for Production)

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**macOS (Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download installer from [postgresql.org](https://www.postgresql.org/download/windows/)

#### Create Database and User

```bash
# Access PostgreSQL shell
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE rememberizer;
CREATE USER rememberizer_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE rememberizer TO rememberizer_user;
\q
```

#### Configure Application

**Option 1: Environment Variable**
```bash
export DATABASE_URL="postgresql://rememberizer_user:your_secure_password@localhost/rememberizer"
```

**Option 2: Update app.py**
```python
# In app.py, replace:
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

# With:
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://rememberizer_user:your_secure_password@localhost/rememberizer"
)
```

#### Install PostgreSQL Adapter

```bash
pip install psycopg2-binary
```

#### Initialize Database

```bash
python init_database.py
```

## First-Time Admin Setup

### Interactive Setup (Default)

On first run, the application prompts for admin account creation:

```bash
python app.py
```

**Prompts:**
1. "No admin account found. Create one now? [Y/n]" → Enter `Y`
2. "Enter admin email:" → Enter valid email (e.g., `admin@school.edu`)
3. "Enter admin password (min 8 chars):" → Enter secure password

**Security Notes:**
- Password is hashed with scrypt before storage
- Password never appears in logs or code
- Only you (the installer) know the admin password
- Setup only runs once (when no admin exists)

### Manual Admin Creation (Advanced)

If you need to create an admin account manually:

```python
# In Python shell:
from app import app, db
from models import User, Organization
from werkzeug.security import generate_password_hash

with app.app_context():
    # Get default organization
    org = Organization.query.get(1)

    # Create admin user
    admin = User(
        email='admin@example.com',
        password_hash=generate_password_hash('your_password'),
        role='admin',
        first_name='Admin',
        last_name='User',
        organization_id=org.id,
        is_active=True
    )

    db.session.add(admin)
    db.session.commit()
    print(f"Admin created: {admin.email}")
```

### Reset Admin Password

If you forget the admin password:

**Option 1: Delete database and recreate** (development only):
```bash
rm instance/database.db
python app.py  # Will prompt for new admin
```

**Option 2: Update password directly**:
```python
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(email='admin@example.com').first()
    admin.password_hash = generate_password_hash('new_password')
    db.session.commit()
    print("Password reset successfully")
```

## Configuration

### Secret Key Configuration

**Generate a secure secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Output example: `a1b2c3d4e5f6...` (64 characters)

**Set in environment variable (recommended):**
```bash
export SECRET_KEY="your_generated_key_here"
```

**Or hardcode in app.py (not recommended for production):**
```python
app.config["SECRET_KEY"] = "your_generated_key_here"
```

### Session Configuration

**app.py settings:**
```python
# Session lifetime (default: 31 days)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=1)

# Session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access
app.config["SESSION_COOKIE_SECURE"] = True    # HTTPS only (production)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax" # CSRF protection
```

### Database Configuration

**SQLite (development):**
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
```

**PostgreSQL (production):**
```python
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost/dbname"
)
```

**MySQL (alternative):**
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://user:password@localhost/dbname"
# Also install: pip install mysqlclient
```

### Email Configuration (Optional)

For automatic setup link delivery via email:

```python
# In app.py, add:
app.config["MAIL_SERVER"] = "smtp.gmail.com"         # Or your SMTP server
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = "noreply@example.com"
```

**Set environment variables:**
```bash
export MAIL_USERNAME="your_email@gmail.com"
export MAIL_PASSWORD="your_app_password"
```

**Note**: Gmail requires [App Passwords](https://support.google.com/accounts/answer/185833) if 2FA is enabled.

### Environment Variables Summary

Create a `.env` file (add to `.gitignore`):

```bash
# App Configuration
FLASK_ENV=production
SECRET_KEY=your_generated_secret_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost/rememberizer

# Email (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=noreply@example.com

# Session Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

**Load environment variables:**
```bash
# Linux/macOS
export $(cat .env | xargs)

# Or use python-dotenv:
pip install python-dotenv

# In app.py:
from dotenv import load_dotenv
load_dotenv()
```

## Production Deployment

### Option 1: Gunicorn (Linux/macOS)

#### Install Gunicorn

```bash
pip install gunicorn
```

#### Run with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

**Flags explained:**
- `-w 4`: 4 worker processes (adjust based on CPU cores: 2-4 × cores)
- `-b 0.0.0.0:8000`: Bind to all interfaces on port 8000
- `app:app`: Module name and Flask app variable

#### Gunicorn Configuration File

Create `gunicorn_config.py`:

```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
errorlog = "/var/log/rememberizer/error.log"
accesslog = "/var/log/rememberizer/access.log"
loglevel = "info"
```

Run with config:
```bash
gunicorn -c gunicorn_config.py app:app
```

### Option 2: Waitress (Windows-compatible)

#### Install Waitress

```bash
pip install waitress
```

#### Run with Waitress

```bash
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

#### Waitress Script

Create `run_waitress.py`:

```python
from waitress import serve
from app import app

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8000, threads=4)
```

Run:
```bash
python run_waitress.py
```

### Option 3: uWSGI (Advanced)

#### Install uWSGI

```bash
pip install uwsgi
```

#### uWSGI Configuration

Create `uwsgi.ini`:

```ini
[uwsgi]
module = app:app
master = true
processes = 4
threads = 2
socket = /tmp/rememberizer.sock
chmod-socket = 660
vacuum = true
die-on-term = true
```

Run:
```bash
uwsgi --ini uwsgi.ini
```

### Process Management with Supervisor

#### Install Supervisor

**Ubuntu/Debian:**
```bash
sudo apt install supervisor
```

#### Supervisor Configuration

Create `/etc/supervisor/conf.d/rememberizer.conf`:

```ini
[program:rememberizer]
command=/path/to/venv/bin/gunicorn -c /path/to/gunicorn_config.py app:app
directory=/path/to/rememberizer
user=www-data
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/rememberizer/err.log
stdout_logfile=/var/log/rememberizer/out.log
environment=SECRET_KEY="your_key",DATABASE_URL="postgresql://..."
```

#### Start Service

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rememberizer
sudo supervisorctl status rememberizer
```

### Nginx Reverse Proxy

#### Install Nginx

**Ubuntu/Debian:**
```bash
sudo apt install nginx
```

#### Nginx Configuration

Create `/etc/nginx/sites-available/rememberizer`:

```nginx
server {
    listen 80;
    server_name rememberizer.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rememberizer.example.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/rememberizer.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rememberizer.example.com/privkey.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static files
    location /static {
        alias /path/to/rememberizer/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
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
}
```

#### Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/rememberizer /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### SSL/TLS with Let's Encrypt

#### Install Certbot

**Ubuntu/Debian:**
```bash
sudo apt install certbot python3-certbot-nginx
```

#### Obtain Certificate

```bash
sudo certbot --nginx -d rememberizer.example.com
```

Follow prompts to configure HTTPS.

#### Auto-renewal

Certbot automatically creates a renewal cron job. Test renewal:
```bash
sudo certbot renew --dry-run
```

### Firewall Configuration

**UFW (Ubuntu):**
```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable
sudo ufw status
```

**firewalld (CentOS/RHEL):**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Email Configuration

### Option 1: Gmail SMTP

**Requirements:**
- Gmail account
- [App Password](https://support.google.com/accounts/answer/185833) (if 2FA enabled)

**Configuration:**
```python
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "your_email@gmail.com"
app.config["MAIL_PASSWORD"] = "your_app_password"
```

### Option 2: Custom SMTP Server

**Example (Office 365):**
```python
app.config["MAIL_SERVER"] = "smtp.office365.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "user@yourdomain.com"
app.config["MAIL_PASSWORD"] = "password"
```

**Example (SendGrid):**
```python
app.config["MAIL_SERVER"] = "smtp.sendgrid.net"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "apikey"
app.config["MAIL_PASSWORD"] = "your_sendgrid_api_key"
```

### Option 3: No Email (Display Links)

If email is not configured, setup links are displayed in flash messages:

```
Teacher John Doe created successfully!
Setup link (valid 7 days): http://localhost:5000/setup-password/abc123...
Please share this link with the teacher securely.
```

Admin/teacher can copy and share link via other channels (Slack, etc.).

## Database Migrations

### From v2.1 to v3.0 (Add Authentication)

If upgrading from v2.1 (single-user) to v3.0 (multi-user):

```bash
python migration_add_auth.py
```

**This migration:**
1. Creates organizations table
2. Creates users table with auth fields
3. Creates user_domain_assignments table
4. Adds user_id to fact_states table
5. Adds user_id and session_id to attempts table
6. Creates default organization
7. **Deletes all existing FactState and Attempt records** (clean slate)

**Warning**: All existing progress is lost. This is intentional for v3.0.

### From v1.0 to v2.0 (Add FactStates)

```bash
python migration_add_fact_states.py
```

**This migration:**
1. Creates fact_states table
2. Migrates mastery status from attempts
3. Preserves existing attempt data

### Manual Migration (PostgreSQL)

If automatic migration fails:

```sql
-- Create new tables
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(20) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    organization_id INTEGER REFERENCES organizations(id),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    setup_token VARCHAR(100) UNIQUE,
    setup_token_expires TIMESTAMP
);

-- Add indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org ON users(organization_id);

-- Insert default organization
INSERT INTO organizations (id, name) VALUES (1, 'Default Organization');

-- Add user_id to existing tables
ALTER TABLE fact_states ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE attempts ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE attempts ADD COLUMN session_id VARCHAR(50);

-- Create indexes
CREATE INDEX idx_fact_states_user ON fact_states(user_id);
CREATE INDEX idx_attempts_user ON attempts(user_id);
CREATE INDEX idx_attempts_session ON attempts(session_id);
```

## Troubleshooting

### "No module named 'flask'" Error

**Solution:**
```bash
pip install -r requirements.txt
```

Ensure virtual environment is activated.

### "Database locked" Error (SQLite)

**Cause**: Multiple processes accessing SQLite simultaneously.

**Solution:**
- Use PostgreSQL for production
- Or ensure only one gunicorn worker: `gunicorn -w 1 ...`

### "No such column: users.setup_token" Error

**Cause**: Database schema out of date.

**Solution:**
```bash
rm instance/database.db  # Delete old database
python init_database.py  # Recreate with new schema
```

### "Port 5000 already in use" Error

**Solution:**
```bash
# Find process using port 5000
lsof -i :5000        # Linux/macOS
netstat -ano | findstr :5000  # Windows

# Kill process or use different port
python app.py --port 5001
```

### "Admin account already exists" Not Creating Admin

**Expected behavior**: Admin creation only runs once.

**To create additional admin:**
```python
from app import app, db
from models import create_user

with app.app_context():
    admin = create_user(
        email='admin2@example.com',
        password='password123',
        role='admin',
        first_name='Admin',
        last_name='Two',
        organization_id=1
    )
```

### Email Not Sending

**Diagnosis:**
1. Check SMTP credentials are correct
2. Check firewall allows outbound SMTP (port 587/465)
3. Check email provider allows SMTP (some require app passwords)

**Fallback**: Setup links display in UI if email fails.

### Session Expires Immediately

**Cause**: `SESSION_COOKIE_SECURE=True` without HTTPS.

**Solution:**
- Use HTTPS in production
- Or set `SESSION_COOKIE_SECURE=False` (development only)

### Tests Fail After Installation

**Diagnosis:**
```bash
pytest -v  # Verbose output to see which tests fail
```

**Common causes:**
- Old database file exists: `rm instance/database.db`
- Missing test dependencies: `pip install -r requirements-dev.txt`
- Working directory wrong: `cd /path/to/rememberizer`

## Backup and Recovery

### Backup SQLite Database

**Manual backup:**
```bash
cp instance/database.db instance/database.backup.db
```

**Automated daily backup (Linux):**
```bash
# Add to crontab: crontab -e
0 2 * * * cp /path/to/rememberizer/instance/database.db /backup/location/database-$(date +\%Y\%m\%d).db
```

### Backup PostgreSQL Database

**Manual backup:**
```bash
pg_dump rememberizer > rememberizer_backup.sql
```

**Automated daily backup:**
```bash
# Add to crontab
0 2 * * * pg_dump rememberizer | gzip > /backup/location/rememberizer-$(date +\%Y\%m\%d).sql.gz
```

### Restore SQLite Database

```bash
cp instance/database.backup.db instance/database.db
python app.py  # Verify restore
```

### Restore PostgreSQL Database

```bash
psql rememberizer < rememberizer_backup.sql
```

Or:
```bash
gunzip -c rememberizer-20260119.sql.gz | psql rememberizer
```

### Export Data for Migration

**Export all users:**
```python
from app import app
from models import User
import json

with app.app_context():
    users = User.query.all()
    data = [{
        'email': u.email,
        'role': u.role,
        'first_name': u.first_name,
        'last_name': u.last_name
    } for u in users]

    with open('users_export.json', 'w') as f:
        json.dump(data, f, indent=2)
```

**Export all domains:**
```python
from app import app
from models import Domain
import json

with app.app_context():
    domains = Domain.query.all()
    data = [{
        'name': d.name,
        'filename': d.filename
    } for d in domains]

    with open('domains_export.json', 'w') as f:
        json.dump(data, f, indent=2)
```

## Production Checklist

Before deploying to production:

- [ ] Generate and set strong SECRET_KEY
- [ ] Configure PostgreSQL (not SQLite)
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Configure SMTP for email delivery
- [ ] Set up Nginx reverse proxy
- [ ] Obtain SSL/TLS certificate (Let's Encrypt)
- [ ] Configure firewall (allow 80, 443, SSH only)
- [ ] Set up process manager (Supervisor/systemd)
- [ ] Configure automated database backups
- [ ] Set up log rotation
- [ ] Configure monitoring (disk, memory, CPU)
- [ ] Test admin account creation
- [ ] Test teacher account creation
- [ ] Test student account creation and domain assignment
- [ ] Test quiz functionality
- [ ] Run full test suite: `pytest`
- [ ] Verify all environment variables are set
- [ ] Document admin credentials securely
- [ ] Set up SSH key authentication (disable password login)
- [ ] Configure fail2ban (brute force protection)
- [ ] Test backup and restore procedures
- [ ] Set up uptime monitoring (optional)

## Additional Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Flask-SQLAlchemy**: https://flask-sqlalchemy.palletsprojects.com/
- **Flask-Login**: https://flask-login.readthedocs.io/
- **Gunicorn**: https://gunicorn.org/
- **Nginx**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/
- **PostgreSQL**: https://www.postgresql.org/docs/

## Support

For installation issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review logs: `/var/log/rememberizer/` or application output
- File an issue on GitHub with error details
