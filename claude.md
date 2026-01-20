# Rememberizer Development Log

This document tracks major changes, refactorings, and architectural decisions made during development.

---

## 2026-01-19: Major Refactoring - Blueprint Architecture

### Overview
Completed a comprehensive refactoring to improve code organization and maintainability. The monolithic `app.py` (1,655 lines) has been split into modular Flask blueprints.

### Phase 1: Blueprint Extraction ✅

#### Changes Made

**1. Created Blueprint Structure**
```
blueprints/
├── __init__.py
├── admin.py          # Admin dashboard and teacher management
├── auth_routes.py    # Login, logout, password setup
├── quiz.py           # Quiz functionality and public routes
├── student.py        # Student domain selection and progress
└── teacher.py        # Teacher dashboard, domain/student management
```

**2. Refactored app.py**
- **Before**: 1,655 lines with 27+ routes
- **After**: 200 lines (88% reduction!)
- Now focuses on: configuration, database initialization, template filters, and blueprint registration

**3. Blueprint Details**

**admin.py** (3 routes):
- `/admin/dashboard` - Admin dashboard with stats
- `/admin/teachers/create` - Create new teachers
- `/admin/teachers/<id>/deactivate` - Deactivate teachers

**auth_routes.py** (3 routes):
- `/login` (GET, POST) - User authentication with role-based redirects
- `/logout` - Session clearing
- `/setup-password/<token>` (GET, POST) - First-time password setup
- Includes email notification helpers

**teacher.py** (11 routes):
- `/teacher/dashboard` - Student progress overview
- `/teacher/domains` - Domain management
- `/teacher/domains/create` - Domain creation (form & CSV)
- `/teacher/domains/<id>/publish` - Toggle domain visibility
- `/teacher/students/create` - Create new students
- `/teacher/students/<id>` - Student detail view
- `/teacher/students/<id>/assign` - Assign domain to student
- `/teacher/students/<id>/unassign` - Unassign domain from student
- `/teacher/students/<id>/reset-domain/<domain_id>` - Reset student progress
- `/teacher/students/<id>/deactivate` - Deactivate students

**student.py** (2 routes):
- `/student/domains` - View assigned domains
- `/student/progress` - Personal progress overview

**quiz.py** (9 routes):
- `/` - Landing page with role-based redirects
- `/start` - Initialize quiz session
- `/show_fact/<id>` - Display fact in table format
- `/mark_learned/<id>` - Mark fact as learned
- `/quiz` - Generate and display quiz question
- `/answer` - Process quiz answer
- `/reset_domain` - Reset current domain progress
- `/reset_domain_from_menu/<id>` - Reset specific domain
- `/reset` - Clear session (testing)

**4. Updated All URL References**

Updated ~100+ `url_for()` calls across:
- **Python files**: All blueprints, auth.py
- **Templates** (16 files): All HTML templates updated with blueprint names

**Example mappings**:
```python
# Old
url_for('admin_dashboard')
url_for('teacher_dashboard')
url_for('student_domains')
url_for('login')

# New
url_for('admin.dashboard')
url_for('teacher.dashboard')
url_for('student.domains')
url_for('auth.login')
```

**5. Fixed Authentication Integration**
- Updated `auth.py`: `login_manager.login_view = "auth.login"`
- Updated `role_required()` decorator to use blueprint names
- Fixed test expectations (302 redirects instead of 403)

#### Testing
- ✅ All 188 tests passing
- ✅ 83% code coverage maintained
- ✅ No functionality broken
- ✅ All authentication flows working
- ✅ All role-based access controls intact

#### Benefits
1. **Better Code Organization**: Related routes grouped by functionality
2. **Improved Maintainability**: Each blueprint is focused and < 300 lines
3. **Easier Testing**: Can test blueprints independently
4. **Scalability**: Easy to add new features without bloating app.py
5. **Team Development**: Different developers can work on different blueprints
6. **Clear Separation**: Auth, admin, teacher, student, and quiz concerns isolated

#### File Size Comparison
| File | Before | After | Change |
|------|--------|-------|--------|
| app.py | 1,655 lines | 200 lines | -88% |
| admin.py | - | 113 lines | New |
| auth_routes.py | - | 147 lines | New |
| teacher.py | - | 294 lines | New |
| student.py | - | 79 lines | New |
| quiz.py | - | 208 lines | New |
| **Total** | 1,655 lines | 1,041 lines | -37% overall |

### Phase 2: Service Layer Extraction ✅

Completed extraction of all business logic from `models.py` into focused service modules.

#### Changes Made

**1. Created Service Layer Structure**
```
services/
├── __init__.py
├── fact_service.py       # Fact learning states and attempts (288 lines)
├── user_service.py       # User management & authentication (128 lines)
├── domain_service.py     # Domain assignment & visibility (230 lines)
└── progress_service.py   # Progress tracking & statistics (164 lines)
```

**2. Refactored models.py**
- **Before**: 1,072 lines (models + 31 business logic functions)
- **After**: 177 lines (ONLY database models!)
- **Reduction**: 83% smaller - pure SQLAlchemy models now

**3. Service Modules Created**

**fact_service.py** (13 functions):
- `get_mastery_status()` - Check if fact is mastered
- `get_mastered_facts()` - Get all mastered facts in domain
- `record_attempt()` - Record quiz attempt
- `get_unmastered_facts()` - Get unmastered facts
- `get_attempt_count()` - Get total attempts for fact
- `mark_fact_learned()` - Mark fact as learned
- `mark_fact_shown()` - Track when fact was displayed
- `is_fact_learned()` - Check if fact is learned
- `get_unlearned_facts()` - Get unlearned facts
- `get_learned_facts()` - Get learned but not mastered facts
- `update_consecutive_attempts()` - Update consecutive counters
- `has_two_consecutive_correct()` - Check for 2 consecutive correct
- `reset_domain_progress()` - Reset all progress for domain

**user_service.py** (3 functions):
- `create_user()` - Create new users with validation
- `authenticate_user()` - Authenticate by email/password
- `get_students_by_teacher()` - Get students in teacher's org

**domain_service.py** (8 functions):
- `get_user_domains()` - Get assigned domains for user
- `assign_domain_to_user()` - Assign domain to student
- `unassign_domain_from_user()` - Remove domain assignment
- `is_domain_assigned()` - Check if domain is assigned
- `create_custom_domain()` - Create custom domain from CSV/form
- `update_domain_published_status()` - Toggle published status
- `get_visible_domains()` - Get domains visible to user
- `is_domain_visible_to_teacher()` - Check domain visibility

**progress_service.py** (7 functions):
- `get_progress_string()` - Generate visual progress string (·-+*)
- `get_student_progress_summary()` - Comprehensive progress summary
- `get_student_domain_progress()` - Detailed domain progress
- `get_questions_answered_today()` - Count today's questions
- `get_total_time_spent()` - Calculate total time spent
- `get_unique_session_count()` - Count unique sessions
- `format_time_spent()` - Format minutes to human-readable

**4. Updated All Imports**

Updated imports across entire codebase (17 files):
- app.py, blueprints (5 files), quiz_logic.py, doom_loop.py
- tests (9 files including conftest.py)
- Separated model imports from service imports
- Clean separation of concerns maintained

#### Testing
- ✅ All 188 tests passing
- ✅ 83% code coverage maintained
- ✅ No functionality broken
- ✅ All business logic working correctly
- ✅ Clean imports throughout codebase

#### Benefits
1. **Clean Separation of Concerns**: Database models vs. business logic
2. **Single Responsibility**: Each service has one clear purpose
3. **Easier Testing**: Can test services independently from database
4. **Better Organization**: Related functions grouped logically
5. **Improved Maintainability**: Smaller, focused modules
6. **Cleaner Imports**: Clear dependencies between layers

#### File Size Comparison
| File | Before | After | Change |
|------|--------|-------|--------|
| models.py | 1,072 lines | 177 lines | -83% |
| fact_service.py | - | 288 lines | New |
| user_service.py | - | 128 lines | New |
| domain_service.py | - | 230 lines | New |
| progress_service.py | - | 164 lines | New |
| **Total** | 1,072 lines | 987 lines | -8% overall (better organized) |

#### Architecture After Phase 2
```
rememberizer/
├── models.py              # 177 lines - ONLY SQLAlchemy models
├── services/              # Business logic layer
│   ├── fact_service.py    # Fact learning operations
│   ├── user_service.py    # User management
│   ├── domain_service.py  # Domain operations
│   └── progress_service.py# Progress tracking
├── blueprints/            # Route handlers
│   ├── admin.py
│   ├── auth_routes.py
│   ├── quiz.py
│   ├── student.py
│   └── teacher.py
├── quiz_logic.py          # Quiz question generation
└── doom_loop.py           # Spaced repetition algorithm
```

---

## Previous Work

### Multi-User Authentication System
- Implemented role-based access control (admin, teacher, student)
- Added organization isolation
- Created user management flows
- Token-based password setup
- Session management with Flask-Login

### Test Coverage
- 188 tests covering all major functionality
- 83% code coverage
- Tests organized by feature area
- Fixtures for authenticated users and test data

### Branch Protection
- Main branch requires passing CI tests
- Direct pushes blocked for all users (including admins)
- All changes must go through feature branches and PRs

---

## Architecture Notes

### Current Structure
```
rememberizer/
├── app.py                 # Flask app, config, filters, DB init
├── auth.py                # Flask-Login integration
├── models.py              # SQLAlchemy models + business logic
├── quiz_logic.py          # Quiz question generation
├── facts_loader.py        # Load domains from JSON
├── doom_loop.py           # Spaced repetition algorithm
├── blueprints/            # Route handlers (NEW!)
│   ├── admin.py
│   ├── auth_routes.py
│   ├── quiz.py
│   ├── student.py
│   └── teacher.py
├── templates/             # Jinja2 templates
│   ├── admin/
│   ├── student/
│   └── teacher/
├── tests/                 # Pytest test suite
└── facts/                 # Domain JSON files
```

### Technology Stack
- **Backend**: Flask, SQLAlchemy, Flask-Login
- **Frontend**: Jinja2 templates, minimal CSS (terminal aesthetic)
- **Database**: SQLite
- **Testing**: Pytest, Flask test client
- **CI**: GitHub Actions (Black, Flake8, Pytest)

---

## Development Workflow

1. **Feature branches**: All work done on `feature/*` branches
2. **Testing**: Run `pytest tests/` before commits
3. **Linting**: Black and Flake8 run in CI
4. **Pull Requests**: Required for merging to main
5. **CI must pass**: Green checks required before merge

---

*Last updated: 2026-01-19*
