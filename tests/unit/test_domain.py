import pytest
from mju_univ_auth.domain.student_card import (
    StudentCard,
    StudentProfile,
    PersonalContact,
    Address,
)
from mju_univ_auth.domain.student_changelog import (
    StudentChangeLog,
    AcademicStatus,
    ChangeLogEntry,
)

class TestStudentCard:
    def test_instantiation(self):
        """Tests creating a nested StudentCard instance."""
        card = StudentCard(
            student_profile=StudentProfile(student_id="123"),
            personal_contact=PersonalContact(
                email="test@test.com",
                current_residence_address=Address(postal_code="12345", address="Seoul")
            )
        )
        assert card.student_profile.student_id == "123"
        assert card.personal_contact.email == "test@test.com"
        assert card.personal_contact.current_residence_address.address == "Seoul"

    def test_to_dict(self):
        """Tests converting a StudentCard instance to a dictionary."""
        card = StudentCard(
            student_profile=StudentProfile(student_id="123", name_korean="홍길동"),
            personal_contact=PersonalContact(email="test@test.com")
        )
        d = card.model_dump()
        assert isinstance(d, dict)
        assert d['student_profile']['student_id'] == "123"
        assert d['personal_contact']['email'] == "test@test.com"


class TestStudentChangeLog:
    def test_instantiation(self):
        """Tests creating a nested StudentChangeLog instance."""
        log = StudentChangeLog(
            academic_status=AcademicStatus(student_id="123", status="재학"),
            change_log_list=[ChangeLogEntry(change_type="복학")]
        )
        assert log.academic_status.student_id == "123"
        assert len(log.change_log_list) == 1
        assert log.change_log_list[0].change_type == "복학"

    def test_to_dict(self):
        """Tests converting a StudentChangeLog instance to a dictionary."""
        log = StudentChangeLog(
            academic_status=AcademicStatus(student_id="123"),
            cumulative_leave_semesters="2학기",
            change_log_list=[ChangeLogEntry(year="2023")]
        )
        d = log.model_dump()
        assert isinstance(d, dict)
        assert d['academic_status']['student_id'] == "123"
        assert d['cumulative_leave_semesters'] == "2학기"
        assert len(d['change_log_list']) == 1