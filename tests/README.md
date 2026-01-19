# Rememberizer Test Suite

Comprehensive test suite for the Rememberizer multi-user quiz application.

## Test Coverage

The test suite covers:

- **Authentication** (`test_auth.py`): User creation, login/logout, password setup
- **Authorization** (`test_authorization.py`): Role-based access control, organization isolation
- **Multi-User Functionality** (`test_multi_user.py`): Progress isolation, domain assignment, engagement metrics
- **Models** (`test_models.py`): Database model functions (existing)
- **Quiz Logic** (`test_quiz_logic.py`): Quiz functionality (existing)
- **Template Filters** (`test_template_filters.py`): Jinja2 filters (existing)
- **Doom Loop** (`test_doom_loop.py`): Recovery mode logic (existing)
- **Facts Loader** (`test_facts_loader.py`): JSON fact loading (existing)
- **Routes** (`test_routes.py`): Route handlers (existing)

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Authentication tests
pytest tests/test_auth.py

# Authorization tests
pytest tests/test_authorization.py

# Multi-user tests
pytest tests/test_multi_user.py
```

### Run Tests by Marker

```bash
# Run only auth tests
pytest -m auth

# Run only model tests
pytest -m models
```

### Generate Coverage Report

```bash
# Run with coverage (default)
pytest

# View HTML coverage report
# Open htmlcov/index.html in your browser
```

### Verbose Output

```bash
# More detailed output
pytest -vv

# Show print statements
pytest -s
```

## Test Fixtures

The test suite uses pytest fixtures defined in `conftest.py`:

### App Fixtures
- `app`: Test Flask application with temporary database
- `client`: Test client for making requests
- `db_session`: Database session for tests

### User Fixtures
- `admin_user`: Admin user for testing
- `teacher_user`: Teacher user for testing
- `student_user`: Student user for testing
- `second_student`: Second student for isolation tests

### Authenticated Client Fixtures
- `authenticated_admin`: Client logged in as admin
- `authenticated_teacher`: Client logged in as teacher
- `authenticated_student`: Client logged in as student

### Domain Fixtures
- `populated_db`: Database with sample facts
- `assigned_domain`: Domain assigned to student
- `user_with_progress`: Student with quiz progress

## Writing New Tests

### Test Class Structure

```python
class TestFeatureName:
    """Test description."""

    def test_specific_behavior(self, fixture1, fixture2):
        """Test that specific behavior works correctly."""
        # Arrange
        # Act
        # Assert
```

### Using Fixtures

```python
def test_something(app, authenticated_student, assigned_domain):
    """Test with multiple fixtures."""
    with app.app_context():
        # Your test code here
        pass
```

### Markers

Add markers to categorize tests:

```python
@pytest.mark.auth
def test_login():
    pass

@pytest.mark.slow
def test_complex_operation():
    pass
```

## Coverage Goals

- **Overall Coverage**: >90%
- **Critical Paths**: 100% (auth, authorization, progress isolation)
- **Models**: >95%
- **Routes**: >90%
- **Quiz Logic**: >95%

## Continuous Integration

Tests should be run:
- Before every commit (recommended)
- Before every pull request (required)
- On CI/CD pipelines (automated)

## Troubleshooting

### Tests Fail with Database Errors

Make sure you have a clean test environment:
```bash
rm -rf instance/
pytest
```

### Import Errors

Ensure you're running from the project root:
```bash
cd /path/to/rememberizer
pytest
```

### Slow Tests

Run only fast tests:
```bash
pytest -m "not slow"
```
