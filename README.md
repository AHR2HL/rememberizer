# Rememberizer

A terminal-styled Flask web application for quizzing students on facts with spaced repetition and mastery tracking.

## Latest Updates (v2.1)

The app now features enhanced question generation and automatic database setup:
- ✅ **Automatic database initialization** - No manual setup required!
- ✅ **Smart domain name singularization** - Questions now say "Greek Muse" instead of "item"
- ✅ **Fixed spaced repetition timing** - Q3, Q6, Q9... are now predictably reinforcement questions
- ✅ 92 tests (up from 79) with 98% code coverage

### Previous Updates (v2.0)

- ✅ Comprehensive **three-state learning system** with intelligent progression tracking
- ✅ Facts must be shown to users before quizzing (prevents "cold quizzing")
- ✅ Requires 2 consecutive correct answers before moving to next fact
- ✅ Automatically demotes facts to unlearned after 2 consecutive wrong answers
- ✅ Progress reset buttons for quick restarts
- ✅ New `fact_states` table tracks learning progression

## Features

- **Domain-based learning**: Load fact domains from JSON files
- **Multiple-choice quizzing**: 4 options per question with intelligent wrong answer selection
- **Three-state learning system**: Facts progress through Unlearned → Learned → Mastered states
- **Mastery tracking**: Facts are marked as mastered after 6 of 7 correct attempts with most recent correct
- **Smart progression**: Requires 2 consecutive correct answers before moving to next fact
- **Automatic demotion**: Facts return to unlearned after 2 consecutive wrong answers
- **Spaced repetition**: Every 3rd question reinforces a previously mastered fact
- **Progress reset**: Reset progress for any domain with one click
- **Terminal aesthetic**: Green-on-black interface with retro styling
- **Persistent progress**: SQLite database tracks all attempts and learning states across sessions

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install development dependencies (for testing and linting):
```bash
pip install -r requirements-dev.txt
```

## Migrating Existing Databases

If you have an existing database from a previous version, run the migration script to add the new `fact_states` table:

```bash
python migration_add_fact_states.py
```

This will add the new table without affecting your existing data.

## Usage

1. Start the application:
```bash
python app.py
```

The database will be automatically initialized on first run! No manual setup needed.

2. Open your browser to `http://localhost:5000`

3. Select a fact domain from the list

4. Review facts and answer quiz questions

5. Use the **[RESET]** button next to any domain to clear progress for that domain

### Manual Database Initialization (Optional)

If you prefer to initialize the database manually before starting the app:

```bash
python init_db.py
```

This is optional - the database initializes automatically on first request.

## Project Structure

```
rememberizer/
├── app.py                       # Main Flask application & routes
├── models.py                    # SQLite database models & learning state logic
├── quiz_logic.py                # Quiz generation & fact selection
├── facts_loader.py              # JSON fact loading & validation
├── init_db.py                   # Manual database initialization script (optional)
├── migration_add_fact_states.py # Database migration script
├── instance/                    # Flask instance folder (auto-created)
│   └── database.db              # SQLite database (auto-initialized on first run)
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies
├── pytest.ini                   # Pytest configuration
├── pyproject.toml               # Black and Ruff configuration
├── .flake8                      # Flake8 configuration
├── .gitignore                   # Git ignore patterns
├── facts/                       # JSON fact files directory
│   └── greek_muses.json         # Example fact domain (9 Greek muses)
├── tests/                       # Unit tests
│   ├── __init__.py              # Test package marker
│   ├── conftest.py              # Shared test fixtures
│   ├── test_models.py           # Test database models & learning states
│   ├── test_quiz_logic.py       # Test question generation & fact selection
│   ├── test_facts_loader.py     # Test JSON loading & validation
│   └── test_routes.py           # Test Flask routes & flows
├── templates/
│   ├── select_domain.html       # Domain selection page with reset buttons
│   ├── show_fact.html           # Fact display page with Continue button
│   └── quiz.html                # Quiz question page with reset option
└── static/
    ├── style.css                # Terminal styling (green/red on black)
    └── app.js                   # Client-side interactivity
```

## Adding New Fact Domains

Create a JSON file in the `facts/` directory with the following format:

```json
{
  "domain_name": "Domain Name",
  "fields": ["field1", "field2", "field3"],
  "facts": [
    {
      "field1": "value1",
      "field2": "value2",
      "field3": "value3"
    }
  ]
}
```

The application will automatically load all JSON files from the `facts/` directory on startup.

## Testing

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```

## Linting

Format code with Black:
```bash
black .
```

Check style with Flake8:
```bash
flake8 .
```

Run all quality checks:
```bash
black . && flake8 . && pytest
```

## How It Works

### Three-State Learning System

Facts progress through three states:

1. **Unlearned**: Fact has never been shown to the user, or has been demoted after 2 consecutive wrong answers
2. **Learned**: Fact has been displayed and user clicked "Continue" - eligible for quizzing
3. **Mastered**: At least 6 of last 7 attempts correct AND most recent attempt correct (requires 7+ attempts)

### State Transitions

- **Unlearned → Learned**: User views fact and clicks "Continue" button
- **Learned → Mastered**: Achieves 6+ correct in last 7 attempts with most recent correct
- **Learned/Mastered → Unlearned**: 2 consecutive wrong answers (demotion)

### Quiz Flow

1. User selects a domain
2. System shows the first **unlearned** fact
3. User clicks "Continue" to mark fact as **learned**
4. System quizzes the user on that fact
5. If correct: Increment consecutive correct counter
   - If 2 consecutive correct: Move to next unlearned fact (or continue with learned facts)
   - If < 2 consecutive correct: Quiz the same fact again
6. If incorrect: Increment consecutive wrong counter
   - If 2 consecutive wrong: Demote to **unlearned**, show fact again
   - If < 2 consecutive wrong: Show fact again, then re-quiz
7. Once all facts are learned: Continue quizzing learned facts
8. Every 3rd question: Quiz a **mastered** fact for reinforcement (if any exist)

### Question Generation

- Questions ask about a random field of the selected fact
- Correct answer comes from the fact being quizzed
- Wrong answers come from the same field of 3 other random facts
- Options are shuffled to prevent pattern recognition

### User Interface Features

- **Terminal aesthetic**: Retro green-on-black color scheme with Courier New font
- **Continue button**: POST form button to mark facts as learned (prevents accidental navigation)
- **Reset buttons**: Red-colored buttons to reset progress (domain menu and quiz page)
- **Keyboard navigation**: Responsive design with mouse and keyboard support
- **Visual feedback**: Buttons change appearance on hover for better interactivity

## Database Schema

**domains**: Fact domains (e.g., "Greek Muses")
- id, name, filename, field_names (JSON)

**facts**: Individual facts within domains
- id, domain_id, fact_data (JSON)

**attempts**: Quiz attempts
- id, fact_id, field_name, correct (boolean), timestamp

**fact_states**: Learning state tracking (NEW)
- id, fact_id, learned_at (datetime, NULL = unlearned), last_shown_at (datetime)
- consecutive_correct (int), consecutive_wrong (int)

## Key Implementation Details

### Models (`models.py`)
- **FactState model**: Tracks learning state with `learned_at`, `last_shown_at`, and consecutive counters
- **9 helper functions**: Complete API for state management (mark learned, check status, reset progress, etc.)
- **Demotion logic**: Automatically demotes facts to unlearned after 2 consecutive wrong answers
- **Mastery calculation**: 6 of last 7 correct with most recent correct (unchanged from original)

### Quiz Logic (`quiz_logic.py`)
- **State-aware fact selection**: Only quizzes learned facts; returns None for unlearned facts
- **Least-practiced prioritization**: Selects facts with fewest attempts first
- **Reinforcement schedule**: Every 3rd question selects from mastered facts
- **Smart progression**: Tracks pending facts requiring 2 consecutive correct answers

### Routes (`app.py`)
- **6 main routes**: index, start, show_fact, quiz, answer, mark_learned
- **2 reset routes**: reset_domain (from quiz), reset_domain_from_menu (from domain selection)
- **Session management**: Tracks pending quiz facts, consecutive correct requirements, question count
- **State updates**: Records attempts and updates consecutive counters on each answer

### Testing
- **92 comprehensive tests**: Cover all state transitions, edge cases, and new features
- **98% code coverage**: High coverage across all modules
- **Integration tests**: Full quiz flow tests including demotion, reset, and spaced repetition scenarios

## License

MIT

## Test Results

All 92 tests pass:
- 16 tests for facts_loader.py
- 30 tests for models.py (including FactState tests)
- 24 tests for quiz_logic.py (including domain name singularization tests)
- 32 tests for Flask routes (including spaced repetition timing tests)

Code coverage: 98% overall
Code is formatted with Black and passes Flake8 style checks with 0 violations.
