"""Tests for domain creation and visibility features."""

import json
import io
from models import db, Domain, Fact, Organization, User
from services.domain_service import (
    create_custom_domain,
    update_domain_published_status,
    get_visible_domains,
    is_domain_visible_to_teacher,
)
from services.user_service import create_user


def test_create_custom_domain_success(app):
    """Test creating a custom domain with valid data."""
    with app.app_context():
        # Create organization and user
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Create custom domain
        field_names = ["name", "capital", "continent"]
        facts_data = [
            {"name": "France", "capital": "Paris", "continent": "Europe"},
            {"name": "Japan", "capital": "Tokyo", "continent": "Asia"},
            {"name": "Brazil", "capital": "Brasilia", "continent": "South America"},
            {"name": "Egypt", "capital": "Cairo", "continent": "Africa"},
        ]

        domain = create_custom_domain(
            name="World Capitals",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher.id,
            organization_id=org.id,
        )

        # Verify domain created
        assert domain.id is not None
        assert domain.name == "World Capitals"
        assert domain.filename is None  # User-created
        assert domain.created_by == teacher.id
        assert domain.organization_id == org.id
        assert domain.is_published is False  # Private by default
        assert domain.get_field_names() == field_names

        # Verify facts created
        facts = Fact.query.filter_by(domain_id=domain.id).all()
        assert len(facts) == 4
        assert facts[0].get_fact_data() == facts_data[0]


def test_create_custom_domain_duplicate_name(app):
    """Test that duplicate domain names are rejected."""
    with app.app_context():
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Create first domain
        field_names = ["name", "value"]
        facts_data = [
            {"name": "Fact1", "value": "Value1"},
            {"name": "Fact2", "value": "Value2"},
            {"name": "Fact3", "value": "Value3"},
            {"name": "Fact4", "value": "Value4"},
        ]

        create_custom_domain(
            name="Test Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher.id,
            organization_id=org.id,
        )

        # Try to create duplicate
        try:
            create_custom_domain(
                name="Test Domain",
                field_names=field_names,
                facts_data=facts_data,
                created_by=teacher.id,
                organization_id=org.id,
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already exists" in str(e)


def test_create_custom_domain_insufficient_facts(app):
    """Test that domains need at least 4 facts."""
    with app.app_context():
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Try with only 3 facts
        field_names = ["name", "value"]
        facts_data = [
            {"name": "Fact1", "value": "Value1"},
            {"name": "Fact2", "value": "Value2"},
            {"name": "Fact3", "value": "Value3"},
        ]

        try:
            create_custom_domain(
                name="Test Domain",
                field_names=field_names,
                facts_data=facts_data,
                created_by=teacher.id,
                organization_id=org.id,
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "at least 4 facts" in str(e)


def test_create_custom_domain_missing_field(app):
    """Test that all facts must have all fields."""
    with app.app_context():
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Facts missing required field
        field_names = ["name", "value", "category"]
        facts_data = [
            {"name": "Fact1", "value": "Value1"},  # Missing category
            {"name": "Fact2", "value": "Value2", "category": "Cat1"},
            {"name": "Fact3", "value": "Value3", "category": "Cat2"},
            {"name": "Fact4", "value": "Value4", "category": "Cat3"},
        ]

        try:
            create_custom_domain(
                name="Test Domain",
                field_names=field_names,
                facts_data=facts_data,
                created_by=teacher.id,
                organization_id=org.id,
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must have all fields" in str(e)


def test_update_domain_published_status(app):
    """Test publishing and unpublishing domains."""
    with app.app_context():
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Create domain
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Test Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher.id,
            organization_id=org.id,
        )

        # Initially unpublished
        assert domain.is_published is False

        # Publish
        update_domain_published_status(domain.id, True)
        db.session.refresh(domain)
        assert domain.is_published is True

        # Unpublish
        update_domain_published_status(domain.id, False)
        db.session.refresh(domain)
        assert domain.is_published is False


def test_get_visible_domains_published(app):
    """Test that published domains are visible to all teachers."""
    with app.app_context():
        # Create two organizations
        org1 = Organization(name="School 1")
        org2 = Organization(name="School 2")
        db.session.add_all([org1, org2])
        db.session.commit()

        # Create teachers in different orgs
        teacher1 = create_user(
            email="teacher1@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="One",
            organization_id=org1.id,
        )

        teacher2 = create_user(
            email="teacher2@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="Two",
            organization_id=org2.id,
        )

        # Create published domain
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Published Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher1.id,
            organization_id=org1.id,
        )

        # Publish it
        update_domain_published_status(domain.id, True)

        # Both teachers should see it
        visible_to_teacher1 = get_visible_domains(teacher1.id, org1.id)
        visible_to_teacher2 = get_visible_domains(teacher2.id, org2.id)

        assert domain in visible_to_teacher1
        assert domain in visible_to_teacher2


def test_get_visible_domains_org_scoped(app):
    """Test that unpublished domains only visible to same org."""
    with app.app_context():
        # Create two organizations
        org1 = Organization(name="School 1")
        org2 = Organization(name="School 2")
        db.session.add_all([org1, org2])
        db.session.commit()

        # Create teachers in different orgs
        teacher1 = create_user(
            email="teacher1@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="One",
            organization_id=org1.id,
        )

        teacher2 = create_user(
            email="teacher2@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="Two",
            organization_id=org2.id,
        )

        # Create unpublished domain in org1
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Org1 Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher1.id,
            organization_id=org1.id,
        )

        # Domain should be visible to teacher1 but not teacher2
        visible_to_teacher1 = get_visible_domains(teacher1.id, org1.id)
        visible_to_teacher2 = get_visible_domains(teacher2.id, org2.id)

        assert domain in visible_to_teacher1
        assert domain not in visible_to_teacher2


def test_is_domain_visible_to_teacher_published(app):
    """Test visibility check for published domains."""
    with app.app_context():
        org = Organization(name="Test School")
        db.session.add(org)
        db.session.commit()

        teacher = create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=org.id,
        )

        # Create published domain
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Published Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher.id,
            organization_id=org.id,
        )

        update_domain_published_status(domain.id, True)

        # Should be visible
        assert is_domain_visible_to_teacher(domain, teacher) is True


def test_is_domain_visible_to_teacher_same_org(app):
    """Test visibility check for org-scoped domains."""
    with app.app_context():
        org1 = Organization(name="School 1")
        org2 = Organization(name="School 2")
        db.session.add_all([org1, org2])
        db.session.commit()

        teacher1 = create_user(
            email="teacher1@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="One",
            organization_id=org1.id,
        )

        teacher2 = create_user(
            email="teacher2@test.com",
            password="password123",
            role="teacher",
            first_name="Teacher",
            last_name="Two",
            organization_id=org2.id,
        )

        # Create unpublished domain in org1
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Org1 Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher1.id,
            organization_id=org1.id,
        )

        # Visible to teacher1, not to teacher2
        assert is_domain_visible_to_teacher(domain, teacher1) is True
        assert is_domain_visible_to_teacher(domain, teacher2) is False


def test_teacher_can_test_domain(app, authenticated_teacher, teacher_user):
    """Test that teachers can start quiz on visible domains."""
    # Create a published domain
    with app.app_context():
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Test Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher_user.id,
            organization_id=teacher_user.organization_id,
        )

        update_domain_published_status(domain.id, True)
        domain_id = domain.id

    # Test starting quiz
    client = authenticated_teacher
    response = client.post(
        "/start", data={"domain_id": domain_id}, follow_redirects=True
    )
    assert response.status_code == 200


def test_domain_creation_route_requires_auth(app):
    """Test that domain creation requires authentication."""
    from app import app as flask_app

    with flask_app.test_client() as client:
        response = client.get("/teacher/domains/create", follow_redirects=False)
        assert response.status_code == 302  # Redirect to login for unauthenticated


def test_domain_creation_form_post(app, authenticated_teacher):
    """Test creating domain via form POST."""
    client = authenticated_teacher

    form_data = {
        "upload_method": "form",
        "domain_name": "US Presidents",
        "field_names": "name, party, years",
        "facts_json": json.dumps(
            [
                {"name": "Washington", "party": "None", "years": "1789-1797"},
                {"name": "Adams", "party": "Federalist", "years": "1797-1801"},
                {"name": "Jefferson", "party": "Dem-Rep", "years": "1801-1809"},
                {"name": "Lincoln", "party": "Republican", "years": "1861-1865"},
            ]
        ),
    }

    response = client.post(
        "/teacher/domains/create", data=form_data, follow_redirects=True
    )
    assert response.status_code == 200

    # Verify domain created
    with app.app_context():
        domain = Domain.query.filter_by(name="US Presidents").first()
        assert domain is not None
        assert len(domain.facts) == 4


def test_domain_creation_csv_post(app, authenticated_teacher):
    """Test creating domain via CSV upload."""
    client = authenticated_teacher

    # Create CSV content
    csv_content = """name,party,years
Washington,None,1789-1797
Adams,Federalist,1797-1801
Jefferson,Dem-Rep,1801-1809
Lincoln,Republican,1861-1865"""

    csv_file = (io.BytesIO(csv_content.encode()), "presidents.csv")

    form_data = {
        "upload_method": "csv",
        "domain_name": "US Presidents CSV",
        "csv_file": csv_file,
    }

    response = client.post(
        "/teacher/domains/create",
        data=form_data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    # Verify domain created
    with app.app_context():
        domain = Domain.query.filter_by(name="US Presidents CSV").first()
        assert domain is not None
        assert len(domain.facts) == 4


def test_admin_can_access_domains_page(app, authenticated_admin):
    """Test that admins can access the domains testing page."""
    client = authenticated_admin

    response = client.get("/teacher/domains")
    assert response.status_code == 200
    assert b"MY DOMAINS" in response.data or b"TEST DOMAINS" in response.data


def test_admin_can_test_domain(app, authenticated_admin, admin_user):
    """Test that admins can start quiz on visible domains."""
    # Create a published domain
    with app.app_context():
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Admin Test Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=admin_user.id,
            organization_id=admin_user.organization_id,
        )

        update_domain_published_status(domain.id, True)
        domain_id = domain.id

    # Test starting quiz as admin
    client = authenticated_admin
    response = client.post(
        "/start", data={"domain_id": domain_id}, follow_redirects=True
    )
    assert response.status_code == 200


def test_admin_can_see_all_org_domains(app, admin_user):
    """Test that admins can see all domains in their organization."""
    with app.app_context():
        # Create a teacher in same org
        teacher = create_user(
            email="teacher_test@test.com",
            password="password123",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            organization_id=admin_user.organization_id,
        )

        # Create org-scoped domain by teacher
        field_names = ["name", "value"]
        facts_data = [{"name": f"Fact{i}", "value": f"Value{i}"} for i in range(1, 5)]

        domain = create_custom_domain(
            name="Org Domain",
            field_names=field_names,
            facts_data=facts_data,
            created_by=teacher.id,
            organization_id=admin_user.organization_id,
        )

        # Admin should see it (same org)
        visible_domains = get_visible_domains(admin_user.id, admin_user.organization_id)
        assert domain in visible_domains
