"""Tests for multi-user progress isolation and functionality."""

import pytest
from models import Fact
from services.fact_service import (
    is_fact_learned,
    get_learned_facts,
    mark_fact_learned,
    record_attempt,
    reset_domain_progress,
)
from services.progress_service import get_student_domain_progress


class TestProgressIsolation:
    """Test that user progress is properly isolated."""

    def test_student_progress_isolated(
        self, app, student_user, second_student, populated_db
    ):
        """Test that different students have isolated progress."""
        with app.app_context():
            facts = Fact.query.filter_by(domain_id=populated_db.id).all()
            fact1 = facts[0]

            # Student 1 learns fact
            mark_fact_learned(fact1.id, student_user.id)

            # Verify student 1 has it learned
            assert is_fact_learned(fact1.id, student_user.id) is True

            # Verify student 2 does NOT have it learned
            assert is_fact_learned(fact1.id, second_student.id) is False

    def test_attempts_isolated_by_user(
        self, app, student_user, second_student, populated_db
    ):
        """Test that attempts are isolated per user."""
        with app.app_context():
            facts = Fact.query.filter_by(domain_id=populated_db.id).all()
            fact1 = facts[0]

            # Student 1 records attempts
            record_attempt(fact1.id, "name", True, student_user.id, "session1")
            record_attempt(fact1.id, "category", True, student_user.id, "session1")

            # Student 2 records different attempts
            record_attempt(fact1.id, "name", False, second_student.id, "session2")

            # Get attempts for each student
            from models import Attempt

            student1_attempts = Attempt.query.filter_by(user_id=student_user.id).count()
            student2_attempts = Attempt.query.filter_by(
                user_id=second_student.id
            ).count()

            assert student1_attempts == 2
            assert student2_attempts == 1

    def test_reset_only_affects_user(
        self, app, student_user, second_student, populated_db
    ):
        """Test that reset only affects the specific user."""
        with app.app_context():
            facts = Fact.query.filter_by(domain_id=populated_db.id).all()

            # Both students learn some facts
            for fact in facts[:2]:
                mark_fact_learned(fact.id, student_user.id)
                mark_fact_learned(fact.id, second_student.id)

            # Verify both have learned facts
            student1_learned = len(get_learned_facts(populated_db.id, student_user.id))
            student2_learned = len(
                get_learned_facts(populated_db.id, second_student.id)
            )
            assert student1_learned == 2
            assert student2_learned == 2

            # Reset student 1
            reset_domain_progress(populated_db.id, student_user.id)

            # Verify student 1 reset
            student1_learned = len(get_learned_facts(populated_db.id, student_user.id))
            assert student1_learned == 0

            # Verify student 2 unchanged
            student2_learned = len(
                get_learned_facts(populated_db.id, second_student.id)
            )
            assert student2_learned == 2


class TestDomainAssignment:
    """Test domain assignment functionality."""

    def test_assign_domain_to_student(
        self, app, student_user, populated_db, teacher_user
    ):
        """Test assigning a domain to a student."""
        with app.app_context():
            from services.domain_service import assign_domain_to_user, is_domain_assigned

            # Assign domain
            assign_domain_to_user(student_user.id, populated_db.id, teacher_user.id)

            # Verify assigned
            assert is_domain_assigned(student_user.id, populated_db.id) is True

    def test_cannot_assign_duplicate_domain(
        self, app, student_user, assigned_domain, teacher_user
    ):
        """Test that assigning duplicate domain raises error."""
        with app.app_context():
            from services.domain_service import assign_domain_to_user

            with pytest.raises(ValueError, match="already assigned"):
                assign_domain_to_user(
                    student_user.id, assigned_domain.id, teacher_user.id
                )

    def test_unassign_domain_from_student(self, app, student_user, assigned_domain):
        """Test unassigning a domain from a student."""
        with app.app_context():
            from services.domain_service import unassign_domain_from_user, is_domain_assigned

            # Unassign domain
            unassign_domain_from_user(student_user.id, assigned_domain.id)

            # Verify unassigned
            assert is_domain_assigned(student_user.id, assigned_domain.id) is False

    def test_get_user_domains(self, app, student_user, assigned_domain):
        """Test getting assigned domains for a user."""
        with app.app_context():
            from services.domain_service import get_user_domains

            domains = get_user_domains(student_user.id)
            assert len(domains) == 1
            assert domains[0].id == assigned_domain.id


class TestStudentManagement:
    """Test teacher student management functionality."""

    def test_get_students_by_teacher(self, app, teacher_user, student_user):
        """Test retrieving students created by teacher."""
        with app.app_context():
            from services.user_service import get_students_by_teacher

            students = get_students_by_teacher(teacher_user.id)
            assert len(students) >= 1
            assert any(s.id == student_user.id for s in students)

    def test_get_student_progress_summary(self, app, student_user, assigned_domain):
        """Test getting student progress summary."""
        with app.app_context():
            from services.progress_service import get_student_progress_summary

            # Add some progress
            facts = Fact.query.filter_by(domain_id=assigned_domain.id).limit(2).all()
            for fact in facts:
                mark_fact_learned(fact.id, student_user.id)

            # Get summary
            summary = get_student_progress_summary(student_user.id)
            assert summary is not None
            assert summary["total_domains"] >= 1
            assert summary["total_questions"] >= 0

    def test_get_student_domain_progress(
        self, app, user_with_progress, assigned_domain
    ):
        """Test getting detailed domain progress for student."""
        with app.app_context():
            progress = get_student_domain_progress(
                user_with_progress.id, assigned_domain.id
            )

            assert progress is not None
            assert progress["total_facts"] == 5
            assert progress["learned_count"] == 2
            assert progress["attempt_count"] == 5  # 2 facts * 2 attempts + 1 wrong


class TestEngagementMetrics:
    """Test engagement tracking metrics."""

    def test_questions_answered_today(self, app, user_with_progress):
        """Test getting questions answered today."""
        with app.app_context():
            from services.progress_service import get_questions_answered_today

            count = get_questions_answered_today(user_with_progress.id)
            assert count == 5  # From user_with_progress fixture

    def test_total_time_spent(self, app, user_with_progress):
        """Test calculating total time spent."""
        with app.app_context():
            from services.progress_service import get_total_time_spent

            time_spent = get_total_time_spent(user_with_progress.id)
            assert time_spent >= 0  # Should be non-negative

    def test_unique_session_count(self, app, user_with_progress):
        """Test counting unique sessions."""
        with app.app_context():
            from services.progress_service import get_unique_session_count

            session_count = get_unique_session_count(user_with_progress.id)
            assert session_count == 1  # All attempts in fixture use 'session1'

    def test_format_time_spent(self, app):
        """Test time formatting."""
        with app.app_context():
            from services.progress_service import format_time_spent

            assert format_time_spent(30) == "30m"
            assert format_time_spent(60) == "1h"
            assert format_time_spent(90) == "1h 30m"
            assert format_time_spent(125) == "2h 5m"


class TestTeacherStudentOperations:
    """Test teacher operations on students."""

    def test_teacher_can_reset_student_progress(
        self, app, authenticated_teacher, student_user, assigned_domain
    ):
        """Test that teacher can reset student progress."""
        with app.app_context():
            facts = Fact.query.filter_by(domain_id=assigned_domain.id).all()

            # Student makes progress
            for fact in facts[:2]:
                mark_fact_learned(fact.id, student_user.id)

            learned_before = len(get_learned_facts(assigned_domain.id, student_user.id))
            assert learned_before == 2

        # Teacher resets progress
        response = authenticated_teacher.post(
            f"/teacher/students/{student_user.id}/reset-domain/{assigned_domain.id}",
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Verify reset
        with app.app_context():
            learned_after = len(get_learned_facts(assigned_domain.id, student_user.id))
            assert learned_after == 0

    def test_teacher_can_view_student_detail(self, authenticated_teacher, student_user):
        """Test that teacher can view student detail page."""
        response = authenticated_teacher.get(f"/teacher/students/{student_user.id}")
        assert response.status_code == 200
        assert b"ENGAGEMENT METRICS" in response.data

    def test_teacher_cannot_access_other_org_student(self, app, authenticated_teacher):
        """Test that teacher cannot access students from other organizations."""
        with app.app_context():
            # Create other org and student
            from models import Organization, db
            from services.user_service import create_user

            org2 = Organization(name="Other Org")
            db.session.add(org2)
            db.session.commit()

            other_student = create_user(
                email="otherstudent@test.com",
                password="password123",
                role="student",
                first_name="Other",
                last_name="Student",
                organization_id=org2.id,
            )
            db.session.commit()
            other_student_id = other_student.id

        # Try to access other org student
        response = authenticated_teacher.get(f"/teacher/students/{other_student_id}")
        assert response.status_code == 403
