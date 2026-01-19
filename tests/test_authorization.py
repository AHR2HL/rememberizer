"""Tests for role-based authorization."""


class TestAdminRoutes:
    """Test admin route access control."""

    def test_admin_can_access_dashboard(self, authenticated_admin):
        """Test that admin can access admin dashboard."""
        response = authenticated_admin.get("/admin/dashboard")
        assert response.status_code == 200
        assert b"ADMIN CONTROL PANEL" in response.data

    def test_teacher_cannot_access_admin_dashboard(self, authenticated_teacher):
        """Test that teacher cannot access admin dashboard."""
        response = authenticated_teacher.get("/admin/dashboard")
        assert response.status_code == 403

    def test_student_cannot_access_admin_dashboard(self, authenticated_student):
        """Test that student cannot access admin dashboard."""
        response = authenticated_student.get("/admin/dashboard")
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client):
        """Test that unauthenticated users cannot access admin routes."""
        response = client.get("/admin/dashboard", follow_redirects=False)
        # Should get 302 (redirect) or 403 (forbidden) - both deny access
        assert response.status_code in [302, 403]
        if response.status_code == 302:
            assert "/login" in response.location


class TestTeacherRoutes:
    """Test teacher route access control."""

    def test_teacher_can_access_dashboard(self, authenticated_teacher):
        """Test that teacher can access teacher dashboard."""
        response = authenticated_teacher.get("/teacher/dashboard")
        assert response.status_code == 200
        assert b"TEACHER DASHBOARD" in response.data

    def test_admin_can_access_teacher_routes(self, authenticated_admin):
        """Test that admin can access teacher routes."""
        response = authenticated_admin.get("/teacher/dashboard")
        assert response.status_code == 200

    def test_student_cannot_access_teacher_dashboard(self, authenticated_student):
        """Test that student cannot access teacher dashboard."""
        response = authenticated_student.get("/teacher/dashboard")
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_teacher(self, client):
        """Test that unauthenticated users cannot access teacher routes."""
        response = client.get("/teacher/dashboard", follow_redirects=False)
        # Should get 302 (redirect) or 403 (forbidden) - both deny access
        assert response.status_code in [302, 403]
        if response.status_code == 302:
            assert "/login" in response.location


class TestStudentRoutes:
    """Test student route access control."""

    def test_student_can_access_domains(self, authenticated_student):
        """Test that student can access student domains."""
        response = authenticated_student.get("/student/domains")
        assert response.status_code == 200
        assert b"MY DOMAINS" in response.data

    def test_teacher_cannot_access_student_routes(self, authenticated_teacher):
        """Test that teacher cannot access student-specific routes."""
        response = authenticated_teacher.get("/student/domains")
        assert response.status_code == 403

    def test_admin_cannot_access_student_routes(self, authenticated_admin):
        """Test that admin cannot access student-specific routes."""
        response = authenticated_admin.get("/student/domains")
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_student(self, client):
        """Test that unauthenticated users cannot access student routes."""
        response = client.get("/student/domains", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.location


class TestQuizRoutes:
    """Test quiz route access control."""

    def test_unauthenticated_cannot_start_quiz(self, client, populated_db):
        """Test that unauthenticated users cannot start quiz."""
        response = client.post(
            "/start", data={"domain_id": populated_db.id}, follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.location

    def test_student_cannot_access_unassigned_domain(
        self, app, authenticated_student, populated_db
    ):
        """Test that student cannot access unassigned domain."""
        response = authenticated_student.post(
            "/start", data={"domain_id": populated_db.id}, follow_redirects=True
        )
        assert response.status_code == 200
        assert b"have access to this domain" in response.data

    def test_student_can_access_assigned_domain(
        self, authenticated_student, assigned_domain
    ):
        """Test that student can access assigned domain."""
        response = authenticated_student.post(
            "/start", data={"domain_id": assigned_domain.id}, follow_redirects=False
        )
        assert response.status_code == 302
        # Should redirect to show_fact or quiz


class TestOrganizationIsolation:
    """Test that users can only access data from their own organization."""

    def test_teacher_can_only_see_own_org_students(
        self, app, authenticated_teacher, student_user
    ):
        """Test that teacher only sees students from their organization."""
        with app.app_context():
            # Create a second organization and student
            from models import Organization, create_user, db

            org2 = Organization(name="Other Organization")
            db.session.add(org2)
            db.session.commit()

            create_user(
                email="other@test.com",
                password="password123",
                role="student",
                first_name="Other",
                last_name="Student",
                organization_id=org2.id,
            )
            db.session.commit()

        # Access teacher dashboard
        response = authenticated_teacher.get("/teacher/dashboard")
        assert response.status_code == 200

        # Should see own org student
        assert b"student@test.com" in response.data

        # Should NOT see other org student
        assert b"other@test.com" not in response.data
