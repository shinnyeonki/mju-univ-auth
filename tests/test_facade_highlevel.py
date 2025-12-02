import pytest

from mju_univ_auth.facade import MjuUnivAuth
from mju_univ_auth.results import MjuUnivAuthResult, ErrorCode
from mju_univ_auth.domain.student_card import StudentCard


def test_get_student_card_auto_login_success(monkeypatch):
    auth = MjuUnivAuth(user_id='user', user_pw='pw')

    # auth.login이 _session과 _login_result를 성공 상태로 설정하도록 모의합니다
    def fake_login(service='msi'):
        auth._session = object()  # 요청용 Session 객체가 아니어도 로직 검증에는 문제없음
        auth._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=True, data=auth._session)
        return auth

    monkeypatch.setattr(auth, 'login', fake_login)

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

    # 세션이 None으로 유지되며 로그인 결과가 설정되지 않게 login()을 오버라이드합니다
    auth.login = lambda service='msi': auth

    result = auth.get_student_card()

    assert result.error_code == ErrorCode.AUTH_FAILED
    assert '로그인' in result.error_message
    assert not result.success


def test_get_session_returns_stored_login_result_when_failed(monkeypatch):
    ma = MjuUnivAuth(user_id='user3', user_pw='pw3')
    ma._session = None
    ma._login_result = MjuUnivAuthResult(request_succeeded=True, credentials_valid=False, error_code=ErrorCode.AUTH_FAILED, error_message='Invalid credentials')

    result = ma.get_session()
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert result.error_message == 'Invalid credentials'
    assert result.credentials_valid is False
