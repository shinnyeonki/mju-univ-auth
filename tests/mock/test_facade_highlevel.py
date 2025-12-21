import pytest
from unittest.mock import MagicMock

from mju_univ_auth import (
    MjuUnivAuth,
    MjuUnivAuthResult,
    ErrorCode,
    StudentCard,
    StudentProfile,
    StudentChangeLog,
    AcademicStatus,
)
from mju_univ_auth.fetcher.student_card_fetcher import StudentCardFetcher
from mju_univ_auth.fetcher.student_changelog_fetcher import StudentChangeLogFetcher


def test_get_student_card_success(monkeypatch):
    """Tests successful student card fetching."""
    auth = MjuUnivAuth(user_id='user', user_pw='pw')
    auth._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=MagicMock())
    auth._service = 'msi'

    # Mock the fetcher's fetch method
    expected_card = StudentCard(student_profile=StudentProfile(student_id='20200001', name_korean='홍길동'))
    mock_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=expected_card)
    monkeypatch.setattr(StudentCardFetcher, 'fetch', lambda self: mock_result)

    # Call the method
    result = auth.get_student_card()

    # Assert the result
    assert result.success
    assert result.data.student_profile.student_id == '20200001'


def test_get_student_card_with_no_login_attempt():
    """Tests calling get_student_card without a session."""
    auth = MjuUnivAuth(user_id='user2', user_pw='pw2')
    auth._login_result = None

    result = auth.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.SESSION_NOT_EXIST_ERROR
    assert '세션이 없습니다' in result.error_message


def test_get_data_after_failed_login():
    """Tests calling a fetcher after a failed login."""
    auth = MjuUnivAuth(user_id='user3', user_pw='pw3')
    auth._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.INVALID_CREDENTIALS_ERROR)

    result = auth.get_student_card()
    
    assert not result.success
    assert result.error_code == ErrorCode.INVALID_CREDENTIALS_ERROR


def test_get_student_changelog_success(monkeypatch):
    """Tests successful student changelog fetching."""
    auth = MjuUnivAuth(user_id='user', user_pw='pw')
    auth._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=MagicMock())
    auth._service = 'msi'

    # Mock the fetcher's fetch method
    expected_changelog = StudentChangeLog(academic_status=AcademicStatus(student_id='20200001', name='홍길동'))
    mock_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=expected_changelog)
    monkeypatch.setattr(StudentChangeLogFetcher, 'fetch', lambda self: mock_result)

    # Call the method
    result = auth.get_student_changelog()

    # Assert the result
    assert result.success
    assert result.data.academic_status.student_id == '20200001'