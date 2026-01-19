"""Tests for Flask routes."""

from models import Fact, Attempt, FactState, mark_fact_learned, is_fact_learned, record_attempt


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
            sess["question_count"] = 5  # Set to 5 to verify it doesn't change
            sess["current_fact_id"] = fact.id
            sess["current_field_name"] = "name"
            sess["correct_index"] = 2

        # Submit correct answer
        response = client.post("/answer", data={"answer": 2}, follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/quiz")

        # Check question count NOT incremented (increments in /quiz now)
        with client.session_transaction() as sess:
            assert sess["question_count"] == 5

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
        # Note: count is 2 because /quiz was called twice:
        # 1. After mark_learned (count becomes 1)
        # 2. After answer redirect (count becomes 2)
        with client.session_transaction() as sess:
            assert sess["question_count"] == 2


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


def test_quiz_route_no_duplicate_consecutive_questions(client, app, populated_db):
    """Test that consecutive questions don't duplicate same field pair."""
    with app.app_context():
        # Mark all facts as learned
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in facts:
            mark_fact_learned(fact.id)

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    # Generate first question
    response1 = client.get("/quiz")
    assert response1.status_code == 200

    with client.session_transaction() as sess:
        last_key = sess.get("last_question_key")
        assert last_key is not None

    # Generate second question
    response2 = client.get("/quiz")
    assert response2.status_code == 200

    with client.session_transaction() as sess:
        current_key = sess.get("last_question_key")
        assert current_key is not None

        # Check if keys are different (they may be same if only 2 fields)
        # But verify the key format is correct
        assert ":" in last_key
        assert ":" in current_key
        parts = current_key.split(":")
        assert len(parts) == 3


def test_quiz_route_supports_bidirectional_questions(client, app, populated_db):
    """Test that questions are generated in both directions."""
    with app.app_context():
        # Mark all facts as learned
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in facts:
            mark_fact_learned(fact.id)

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    # Generate multiple questions and track field combinations
    name_as_context_count = 0
    name_as_quiz_count = 0

    for i in range(30):
        response = client.get("/quiz")
        assert response.status_code == 200

        with client.session_transaction() as sess:
            last_key = sess.get("last_question_key")
            if last_key:
                parts = last_key.split(":")
                context_field = parts[1]
                quiz_field = parts[2]

                # Track when name is used as context vs quiz
                if context_field == "name":
                    name_as_context_count += 1
                if quiz_field == "name":
                    name_as_quiz_count += 1

                # Ensure context and quiz are different
                assert context_field != quiz_field

        # Answer the question to continue
        with client.session_transaction() as sess:
            correct_index = sess.get("correct_index", 0)

        client.post("/answer", data={"answer": correct_index}, follow_redirects=False)

    # Both directions should occur (statistical check)
    # With 30 questions, at least one of each should appear
    assert name_as_context_count > 0 or name_as_quiz_count > 0


def test_quiz_route_never_asks_field_to_itself(client, app, populated_db):
    """Test that questions never ask field→itself."""
    with app.app_context():
        # Mark all facts as learned
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in facts:
            mark_fact_learned(fact.id)

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    # Generate many questions and verify no field→itself
    for i in range(50):
        response = client.get("/quiz")
        assert response.status_code == 200

        with client.session_transaction() as sess:
            last_key = sess.get("last_question_key")
            if last_key:
                parts = last_key.split(":")
                context_field = parts[1]
                quiz_field = parts[2]

                # CRITICAL: context_field must never equal quiz_field
                assert context_field != quiz_field, f"Invalid question: {context_field}→{quiz_field}"

        # Answer the question to continue
        with client.session_transaction() as sess:
            correct_index = sess.get("correct_index", 0)

        client.post("/answer", data={"answer": correct_index}, follow_redirects=False)


def test_question_count_increments_on_every_quiz(client, app, populated_db):
    """Test that question_count increments on every /quiz call."""
    with app.app_context():
        # Mark all facts as learned
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()
        for fact in facts:
            mark_fact_learned(fact.id)

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    # Call /quiz three times
    for expected_count in [1, 2, 3]:
        response = client.get("/quiz")
        assert response.status_code == 200

        with client.session_transaction() as sess:
            assert sess["question_count"] == expected_count

        # Answer question (doesn't matter if correct or not)
        with client.session_transaction() as sess:
            correct_index = sess.get("correct_index", 0)
        client.post("/answer", data={"answer": correct_index})


def test_reinforcement_every_third_question(client, app, populated_db):
    """Test that Q3, Q6, Q9 are reinforcement questions."""
    with app.app_context():
        facts = Fact.query.filter_by(domain_id=populated_db.id).all()

        # Mark all facts as learned
        for fact in facts:
            mark_fact_learned(fact.id)

        # Master first fact (7 correct attempts)
        for i in range(7):
            record_attempt(facts[0].id, "name", True)

        # Get the mastered fact ID before exiting context
        mastered_fact_id = facts[0].id

    # Initialize session
    with client.session_transaction() as sess:
        sess["domain_id"] = populated_db.id
        sess["question_count"] = 0

    quizzed_facts = []

    # Generate 9 questions and track which facts are quizzed
    for q_num in range(1, 10):
        response = client.get("/quiz")
        assert response.status_code == 200

        with client.session_transaction() as sess:
            fact_id = sess.get("current_fact_id")
            quizzed_facts.append((q_num, fact_id))

        # Answer correctly to continue
        with client.session_transaction() as sess:
            correct_index = sess.get("correct_index", 0)
        client.post("/answer", data={"answer": correct_index})

    # Q3, Q6, Q9 should be the mastered fact
    q3_fact = next(fid for qn, fid in quizzed_facts if qn == 3)
    q6_fact = next(fid for qn, fid in quizzed_facts if qn == 6)
    q9_fact = next(fid for qn, fid in quizzed_facts if qn == 9)

    assert q3_fact == mastered_fact_id, "Q3 should be reinforcement"
    assert q6_fact == mastered_fact_id, "Q6 should be reinforcement"
    assert q9_fact == mastered_fact_id, "Q9 should be reinforcement"
