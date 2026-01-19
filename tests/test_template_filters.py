"""Tests for custom Jinja2 template filters."""


def test_center_in_box_greek_muses(app):
    """Test centering 'GREEK MUSES'."""
    with app.app_context():
        from app import center_in_box
        result = center_in_box("GREEK MUSES")
        assert len(result) == 35
        assert result.strip() == "GREEK MUSES"
        # 11 chars text, 24 chars padding


def test_center_in_box_rememberizer(app):
    """Test centering 'REMEMBERIZER v1.0'."""
    with app.app_context():
        from app import center_in_box
        result = center_in_box("REMEMBERIZER v1.0")
        assert len(result) == 35
        assert result.strip() == "REMEMBERIZER v1.0"


def test_center_in_box_empty_text(app):
    """Test centering empty string."""
    with app.app_context():
        from app import center_in_box
        result = center_in_box("")
        assert len(result) == 35
        assert result == " " * 35


def test_center_in_box_custom_width(app):
    """Test centering with custom width."""
    with app.app_context():
        from app import center_in_box
        result = center_in_box("TEST", width=10)
        assert len(result) == 10
        assert result.strip() == "TEST"


def test_center_in_box_strips_whitespace(app):
    """Test that extra spaces are stripped."""
    with app.app_context():
        from app import center_in_box
        result = center_in_box("  GREEK MUSES  ")
        assert result.strip() == "GREEK MUSES"
        assert len(result) == 35
