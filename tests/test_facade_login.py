import pytest

from mju_univ_auth.facade import MjuUnivAuth
from mju_univ_auth.results import MjuUnivAuthResult, ErrorCode


def test_get_student_card_returns_stored_failed_login_result(monkeypatch):
    ma = MjuUnivAuth(user_id='user', user_pw='pw')
    ma._session = None
    ma._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.AUTH_FAILED, error_message='Invalid credentials')

    # _ensure_login이 실제 네트워크 호출을 하지 않도록 login()을 오버라이드합니다
    ma.login = lambda service='msi': ma

    result = ma.get_student_card()

    assert result is not None
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert result.error_message == 'Invalid credentials'
    assert not result.success


def test_get_student_card_with_no_login_attempt(monkeypatch):
    ma = MjuUnivAuth(user_id='user2', user_pw='pw2')
    ma._session = None
    ma._login_result = None

    # 세션이 None으로 유지되며 로그인 결과가 설정되지 않게 login()을 오버라이드합니다
    ma.login = lambda service='msi': ma

    result = ma.get_student_card()

    assert result.error_code == ErrorCode.AUTH_FAILED
    assert '로그인' in result.error_message
    assert not result.success


def test_get_session_returns_stored_login_result_when_failed(monkeypatch):
    ma = MjuUnivAuth(user_id='user3', user_pw='pw3')
    ma._session = None
    ma._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.AUTH_FAILED, error_message='Invalid credentials')

    # get_session()은 기본 메시지 대신 저장된 실패한 로그인 결과를 반환해야 합니다
    result = ma.get_session()
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert result.error_message == 'Invalid credentials'
    assert result.credentials_valid is False
