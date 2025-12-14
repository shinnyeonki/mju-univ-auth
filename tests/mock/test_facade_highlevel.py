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

    # auth._create_fresh_session이 성공적인 로그인 결과를 반환하도록 모의합니다
    def fake_create_fresh_session(service='msi'):
        session = object()
        return MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=session)

    monkeypatch.setattr(auth, '_create_fresh_session', fake_create_fresh_session)

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
    auth._login_result = None

    # _create_fresh_session이 실패 결과를 반환하도록 모의합니다
    def fake_create_fresh_session(service='msi'):
        return MjuUnivAuthResult(
            request_succeeded=False,
            error_code=ErrorCode.AUTH_FAILED,
            error_message="로그인이 필요합니다."
        )

    monkeypatch.setattr(auth, '_create_fresh_session', fake_create_fresh_session)

    result = auth.get_student_card()

    assert result.error_code == ErrorCode.AUTH_FAILED
    assert '로그인이 필요합니다' in result.error_message
    assert not result.success


def test_get_session_returns_stored_login_result_when_failed(monkeypatch):
    ma = MjuUnivAuth(user_id='user3', user_pw='pw3')
    ma._session = None
    ma._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.AUTH_FAILED, error_message='Invalid credentials')

    result = ma.get_session()
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert result.error_message == 'Invalid credentials'
    assert result.credentials_valid is False


def test_get_student_changelog_success(monkeypatch):
    auth = MjuUnivAuth(user_id='user', user_pw='pw')

    # Mock successful login
    def fake_create_fresh_session(service='msi'):
        session = object()
        return MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=session)
    monkeypatch.setattr(auth, '_create_fresh_session', fake_create_fresh_session)

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