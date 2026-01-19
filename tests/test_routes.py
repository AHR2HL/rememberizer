"""Tests for Flask routes."""

from models import Fact, Attempt, FactState, mark_fact_learned, is_fact_learned


def test_index_route(client, populated_db):
    """Test the index route displays domain selection."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"SELECT FACT DOMAIN" in response.data


def test_start_route(client, populated_db):
    """Test starting a quiz session."""
    response = client.post(
        "/start", data={"domain_id": populated_db.id}, follow_redirects=False
    )
    assert response.status_code == 302  # Redirect

    # Check session was initialized
    with client.session_transaction() as sess:
        assert sess.get("domain_id") == populated_db.id
        assert sess.get("question_count") == 0


def test_start_route_invalid_domain(client):
    """Test starting with invalid domain ID redirects to index."""
    response = client.post("/start", data={"domain_id": 999}, follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_start_route_no_domain(client):
    """Test starting without domain ID redirects to index."""
    response = client.post("/start", data={}, follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_show_fact_route(client, app, populated_db):
    """Test displaying a fact."""
    with app.app_context():
        fact = Fact.query.first()
        response = client.get(f"/show_fact/{fact.id}")

        assert response.status_code == 200
        assert b"FACT DISPLAY" in response.data

        fact_data = fact.get_fact_data()
        for value in fact_data.values():
            assert value.encode() in response.data


def test_show_fact_route_invalid_id(client):
    """Test showing fact with invalid ID returns 404."""
    response = client.get("/show_fact/999")
    assert response.status_code == 404


def test_quiz_route(client, app, populated_db):
    """Test displaying a quiz question."""
    with app.app_context():
        # Mark all facts as learned so quiz can proceed
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in facts:
            mark_fact_learned(fact.id)

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    response = client.get("/quiz")
    assert response.status_code == 200
    assert b"QUIZ" in response.data

    # Check that session has current question data
    with client.session_transaction() as sess:
        assert "current_fact_id" in sess
        assert "current_field_name" in sess
        assert "correct_index" in sess


def test_quiz_route_no_session(client):
    """Test quiz route without session redirects to index."""
    response = client.get("/quiz", follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_answer_route_correct(client, app, populated_db):
    """Test submitting a correct answer."""
    with app.app_context():
        fact = Fact.query.first()

        # Mark fact as learned
        mark_fact_learned(fact.id)

        # Initialize session
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 0
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        # Submit correct answer
        response = client.post("/answer", data={"answer": 2}, follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/quiz")

        # Check question count incremented
        with client.session_transaction() as sess:
            assert sess["question_count"] == 1

        # Check attempt was recorded
        attempt = Attempt.query.filter_by(fact_id=fact.id).first()
        assert attempt is not None
        assert attempt.correct is True


def test_answer_route_incorrect(client, app, populated_db):
    """Test submitting an incorrect answer."""
    with app.app_context():
        fact = Fact.query.first()

        # Mark fact as learned
        mark_fact_learned(fact.id)

        # Initialize session
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 0
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        # Submit incorrect answer
        response = client.post("/answer", data={"answer": 1}, follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith(f"/show_fact/{fact.id}")

        # Check question count not incremented
        with client.session_transaction() as sess:
            assert sess["question_count"] == 0

        # Check attempt was recorded
        attempt = Attempt.query.filter_by(fact_id=fact.id).first()
        assert attempt is not None
        assert attempt.correct is False


def test_answer_route_no_answer(client):
    """Test submitting without answer returns 400."""
    response = client.post("/answer", data={})
    assert response.status_code == 400


def test_answer_route_no_session(client):
    """Test answer route without session redirects to index."""
    response = client.post("/answer", data={"answer": 1}, follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")


def test_reset_route(client, app, populated_db):
    """Test resetting the session."""
    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 5

    response = client.post("/reset", follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith("/")

    # Check session was cleared
    with client.session_transaction() as sess:
        assert "domain_id" not in sess
        assert "question_count" not in sess


def test_full_quiz_flow(client, app, populated_db):
    """Test complete quiz flow: start -> show fact -> quiz -> answer."""
    with app.app_context():
        # Start quiz
        response = client.post(
            "/start", data={"domain_id": populated_db.id}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"FACT DISPLAY" in response.data

        # Get fact ID from URL
        fact_id = response.request.path.split("/")[-1]

        # Mark fact as learned
        response = client.post(f"/mark_learned/{fact_id}", follow_redirects=True)
        assert response.status_code == 200
        assert b"QUIZ" in response.data

        # Get correct answer from session
        with client.session_transaction() as sess:
            correct_index = sess["correct_index"]

        # Submit correct answer
        response = client.post(
            "/answer", data={"answer": correct_index}, follow_redirects=True
        )
        assert response.status_code == 200
        # Should redirect to quiz (may show fact or quiz next)
        assert response.status_code == 200

        # Verify question count incremented
        with client.session_transaction() as sess:
            assert sess["question_count"] == 1


def test_mark_learned_route(client, app, populated_db):
    """Test marking a fact as learned."""
    with app.app_context():
        fact = Fact.query.first()

        # Initialize session
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 0

        # Mark fact as learned
        response = client.post(f"/mark_learned/{fact.id}", follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/quiz")

        # Verify fact is marked as learned
        assert is_fact_learned(fact.id) is True

        # Verify pending quiz fact is set
        with client.session_transaction() as sess:
            assert sess.get("pending_quiz_fact_id") == fact.id


def test_reset_domain_route(client, app, populated_db):
    """Test resetting domain progress."""
    with app.app_context():
        fact = Fact.query.first()

        # Add some progress
        mark_fact_learned(fact.id)
        from models import record_attempt

        record_attempt(fact.id, "name", True)

        # Initialize session
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 5

        # Reset domain
        response = client.post("/reset_domain", follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/")

        # Check session was cleared
        with client.session_transaction() as sess:
            assert "domain_id" not in sess
            assert "question_count" not in sess

        # Check progress was cleared
        assert Attempt.query.filter_by(fact_id=fact.id).count() == 0
        assert FactState.query.filter_by(fact_id=fact.id).count() == 0


def test_reset_domain_from_menu_route(client, app, populated_db):
    """Test resetting domain from menu."""
    with app.app_context():
        fact = Fact.query.first()

        # Add some progress
        mark_fact_learned(fact.id)
        from models import record_attempt

        record_attempt(fact.id, "name", True)

        # Reset domain from menu
        response = client.post(
            f"/reset_domain_from_menu/{populated_db.id}", follow_redirects=False
        )
        assert response.status_code == 302
        assert response.location.endswith("/")

        # Check progress was cleared
        assert Attempt.query.filter_by(fact_id=fact.id).count() == 0
        assert FactState.query.filter_by(fact_id=fact.id).count() == 0


def test_demotion_flow(client, app, populated_db):
    """Test demotion to unlearned after 2 consecutive wrong answers."""
    with app.app_context():
        fact = Fact.query.first()

        # Mark fact as learned
        mark_fact_learned(fact.id)
        assert is_fact_learned(fact.id) is True

        # Initialize session
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 0
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        # First wrong answer
        response = client.post("/answer", data={"answer": 1}, follow_redirects=False)
        assert response.status_code == 302
        assert is_fact_learned(fact.id) is True  # Still learned

        # Second wrong answer - should demote
        with client.session_transaction() as sess:
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        response = client.post("/answer", data={"answer": 1}, follow_redirects=False)
        assert response.status_code == 302
        assert is_fact_learned(fact.id) is False  # Demoted to unlearned


def test_two_consecutive_correct_flow(client, app, populated_db):
    """Test that 2 consecutive correct answers clears pending quiz fact."""
    with app.app_context():
        fact = Fact.query.first()

        # Mark fact as learned
        mark_fact_learned(fact.id)

        # Initialize session with pending quiz fact
        with client.session_transaction() as sess:
            sess["domain_id"] = populated_db.id
            sess["question_count"] = 0
            sess["pending_quiz_fact_id"] = fact.id
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        # First correct answer
        response = client.post("/answer", data={"answer": 2}, follow_redirects=False)
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("pending_quiz_fact_id") == fact.id  # Still pending

        # Second correct answer - should clear pending
        with client.session_transaction() as sess:
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        response = client.post("/answer", data={"answer": 2}, follow_redirects=False)
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert "pending_quiz_fact_id" not in sess  # Cleared
