import pytest

from mju_univ_auth import (
    MjuUnivAuth,
    MjuUnivAuthResult,
    ErrorCode,
    StudentCard,
    StudentChangeLog,
)


def test_get_student_card_auto_login_success(monkeypatch):
    auth = MjuUnivAuth(user_id='user', user_pw='pw')

    # Set a mock session and service
    mock_session = object()
    auth._session = mock_session
    auth._service = 'msi'

    # StudentCardFetcher를 모의로 바꿔 예상 결과를 반환하도록 합니다
    expected_card = StudentCard(student_id='20200001', name_korean='홍길동')
    def fake_fetcher(session=None, user_pw=None, verbose=False):
        class F:
            def fetch(self):
                return MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=expected_card)
        return F()

    monkeypatch.setattr('mju_univ_auth.facade.StudentCardFetcher', fake_fetcher)

    result = auth.get_student_card()

    assert result.success
    assert result.data.student_id == '20200001'


def test_get_student_card_with_no_login_attempt(monkeypatch):
    auth = MjuUnivAuth(user_id='user2', user_pw='pw2')
    auth._session = None
    auth._login_failed = False
    auth._login_error = None

    result = auth.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.SESSION_NOT_EXIST_ERROR
    assert '세션이 없습니다' in result.error_message


def test_get_session_returns_stored_login_result_when_failed(monkeypatch):
    ma = MjuUnivAuth(user_id='user3', user_pw='pw3')
    ma._session = None
    ma._login_failed = True
    ma._login_error = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.INVALID_CREDENTIALS_ERROR, error_message='Invalid credentials')

    result = ma.get_session()
    
    assert not result.success
    assert result.error_code == ErrorCode.INVALID_CREDENTIALS_ERROR
    assert result.error_message == 'Invalid credentials'
    assert result.credentials_valid is False


def test_get_student_changelog_success(monkeypatch):
    auth = MjuUnivAuth(user_id='user', user_pw='pw')

    # Set a mock session and service
    mock_session = object()
    auth._session = mock_session
    auth._service = 'msi'

    # Mock StudentChangeLogFetcher
    expected_changelog = StudentChangeLog(student_id='20200001', name='홍길동')
    def fake_fetcher(session=None, verbose=False):
        class F:
            def fetch(self):
                return MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=expected_changelog)
        return F()
    monkeypatch.setattr('mju_univ_auth.facade.StudentChangeLogFetcher', fake_fetcher)

    result = auth.get_student_changelog()

    assert result.success
    assert result.data.student_id == '20200001'
