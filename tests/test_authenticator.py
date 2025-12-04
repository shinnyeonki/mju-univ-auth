import requests
import pytest

from mju_univ_auth.authenticator import Authenticator
from mju_univ_auth.standard_authenticator import StandardAuthenticator
from mju_univ_auth.exceptions import InvalidCredentialsError
from mju_univ_auth.results import ErrorCode


def test_authenticator_login_success(monkeypatch):
    auth = Authenticator(user_id='student', user_pw='pw')

    # StandardAuthenticator.authenticate를 모의로 바꿔 성공 결과를 반환하도록 합니다
    from mju_univ_auth.results import MjuUnivAuthResult
    
    def fake_authenticate(self):
        return MjuUnivAuthResult(
            request_succeeded=True,
            credentials_valid=True,
            data=requests.Session()
        )

    monkeypatch.setattr(StandardAuthenticator, 'authenticate', fake_authenticate)

    result = auth.login(service='msi')

    assert result.request_succeeded
    assert result.credentials_valid
    assert result.data is not None
    assert isinstance(result.data, requests.Session)


def test_authenticator_login_invalid_credentials(monkeypatch):
    auth = Authenticator(user_id='bad', user_pw='pw')

    from mju_univ_auth.results import MjuUnivAuthResult
    
    def fake_authenticate(self):
        return MjuUnivAuthResult(
            request_succeeded=True,
            credentials_valid=False,
            error_code=ErrorCode.AUTH_FAILED,
            error_message='Invalid credentials'
        )

    monkeypatch.setattr(StandardAuthenticator, 'authenticate', fake_authenticate)

    result = auth.login(service='msi')

    assert result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert 'Invalid' in result.error_message


def test_authenticator_login_unknown_service():
    auth = Authenticator(user_id='id', user_pw='pw')

    result = auth.login(service='i_do_not_exist')

    assert not result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.SERVICE_NOT_FOUND
    assert '알 수 없는 서비스' in result.error_message
