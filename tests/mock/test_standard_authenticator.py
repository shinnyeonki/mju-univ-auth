import requests
import pytest

from mju_univ_auth import (
    StandardAuthenticator,
    InvalidCredentialsError,
    ErrorCode,
)


def test_authenticator_login_success(monkeypatch):
    auth = StandardAuthenticator(user_id='student', user_pw='pw')

    # 내부 _execute_login을 모의로 바꿔 예외를 발생시키지 않게 하고 세션이 통과되도록 합니다
    def fake_execute(session, service):
        # 아무 동작도 하지 않고 세션을 그대로 사용합니다
        return None

    monkeypatch.setattr(auth, '_execute_login', fake_execute)

    result = auth.login(service='msi')

    assert result.request_succeeded
    assert result.credentials_valid
    assert result.data is not None
    assert isinstance(result.data, requests.Session)


def test_authenticator_login_invalid_credentials(monkeypatch):
    auth = StandardAuthenticator(user_id='bad', user_pw='pw')

    def fake_execute(session, service):
        raise InvalidCredentialsError('Invalid credentials', service='MSI')

    monkeypatch.setattr(auth, '_execute_login', fake_execute)

    result = auth.login(service='msi')

    assert result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert 'Invalid' in result.error_message


def test_authenticator_login_unknown_service():
    auth = StandardAuthenticator(user_id='id', user_pw='pw')

    result = auth.login(service='i_do_not_exist')

    assert not result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.SERVICE_NOT_FOUND
    assert '알 수 없는 서비스' in result.error_message


def test_authenticator_login_unknown_error(monkeypatch):
    auth = StandardAuthenticator(user_id='id', user_pw='pw')

    def fake_execute(session, service):
        raise ValueError('Something went wrong')

    monkeypatch.setattr(auth, '_execute_login', fake_execute)

    result = auth.login(service='msi')

    assert not result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.UNKNOWN
    assert 'Something went wrong' in result.error_message