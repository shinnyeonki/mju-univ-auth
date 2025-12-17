"""
에러 핸들링 테스트
==================
MjuUnivAuth Facade가 다양한 에러 상황을 어떻게 처리하고
올바른 MjuUnivAuthResult를 반환하는지 검증합니다.
"""

import pytest
from unittest.mock import MagicMock, patch

from mju_univ_auth import MjuUnivAuth, MjuUnivAuthResult, ErrorCode
from mju_univ_auth.authenticator.base_authenticator import BaseAuthenticator


@pytest.fixture
def auth_instance():
    """각 테스트를 위한 MjuUnivAuth 인스턴스를 제공합니다."""
    return MjuUnivAuth(user_id="test", user_pw="test")


def test_login_service_not_found(auth_instance, monkeypatch):
    """
    Given: 존재하지 않는 서비스 이름이 주어졌을 때
    When: login 메서드가 호출되면
    Then: 결과는 SERVICE_NOT_FOUND_ERROR 에러를 포함해야 합니다.
    """
    mock_result = MjuUnivAuthResult(
        request_succeeded=False,
        error_code=ErrorCode.SERVICE_NOT_FOUND_ERROR,
        error_message="알 수 없는 서비스: invalid_service"
    )
    monkeypatch.setattr(BaseAuthenticator, 'login', lambda self, service: mock_result)

    # login 메서드는 self를 반환하므로, 내부 상태를 확인합니다.
    auth_instance.login('invalid_service')
    
    assert auth_instance._login_failed is True
    assert auth_instance._login_error is not None
    assert auth_instance._login_error.error_code == ErrorCode.SERVICE_NOT_FOUND_ERROR
    assert "알 수 없는 서비스" in auth_instance._login_error.error_message


def test_get_data_with_invalid_service_usage(auth_instance):
    """
    Given: MSI가 아닌 서비스로 로그인된 세션이 있을 때
    When: MSI가 필요한 메서드(예: get_student_card)가 호출되면
    Then: 결과는 SERVICE_UNKNOWN_ERROR 에러를 포함해야 합니다.
    """
    # 'lms' 서비스로 성공적으로 로그인했다고 가정합니다.
    auth_instance._session = MagicMock()
    auth_instance._service = 'lms'
    auth_instance._login_failed = False

    result = auth_instance.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.INVALID_SERVICE_USAGE_ERROR
    assert "MSI 서비스로 로그인된 세션이 아닙니다" in result.error_message


def test_get_data_with_no_session(auth_instance):
    """
    Given: 로그인이 수행되지 않았을 때
    When: 데이터 조회 메서드가 호출되면
    Then: 결과는 SESSION_NOT_EXIST_ERROR 에러를 포함해야 합니다.
    """
    result = auth_instance.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.SESSION_NOT_EXIST_ERROR
    assert "세션이 없습니다" in result.error_message


def test_login_failure_propagates_to_get_data(auth_instance):
    """
    Given: 초기 로그인 시도가 실패했을 때
    When: 데이터 조회 메서드가 호출되면
    Then: 결과는 원래의 로그인 실패를 반영해야 합니다.
    """
    # 로그인 실패 상황을 가정합니다.
    login_error_result = MjuUnivAuthResult(
        request_succeeded=True,
        credentials_valid=False,
        error_code=ErrorCode.INVALID_CREDENTIALS_ERROR,
        error_message="아이디/비번 틀림"
    )
    auth_instance._login_failed = True
    auth_instance._login_error = login_error_result

    result = auth_instance.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.INVALID_CREDENTIALS_ERROR
    assert result.error_message == "아이디/비번 틀림"


@pytest.mark.parametrize("error_code, error_message, creds_valid", [
    (ErrorCode.NETWORK_ERROR, "네트워크 오류", False),
    (ErrorCode.PARSING_ERROR, "파싱 오류", True),
    (ErrorCode.INVALID_CREDENTIALS_ERROR, "인증 실패", False),
    (ErrorCode.ALREADY_LOGGED_IN_ERROR, "이미 로그인됨", True),
    (ErrorCode.UNKNOWN_ERROR, "알 수 없는 오류", False),
])
def test_login_catches_various_errors(auth_instance, monkeypatch, error_code, error_message, creds_valid):
    """
    Given: Authenticator가 특정 에러와 함께 실패할 때
    When: login 메서드가 호출되면
    Then: Facade는 해당 에러 결과를 정확히 저장해야 합니다.
    """
    mock_result = MjuUnivAuthResult(
        request_succeeded=False,
        credentials_valid=creds_valid,
        error_code=error_code,
        error_message=error_message
    )
    # 슈퍼클래스인 BaseAuthenticator의 login 메서드를 패치합니다.
    monkeypatch.setattr(BaseAuthenticator, 'login', lambda self, service: mock_result)

    auth_instance.login('msi')

    assert auth_instance._login_failed is True
    assert auth_instance._login_error is not None
    assert auth_instance._login_error.error_code == error_code
    assert auth_instance._login_error.error_message == error_message


def test_fetcher_catches_session_expired(auth_instance):
    """
    Given: 유효한 로그인 세션이 존재할 때
    When: Fetcher가 SessionExpiredError를 마주하면
    Then: Facade는 SESSION_EXPIRED_ERROR 에러 결과를 반환해야 합니다.
    """
    # 성공적인 로그인을 가정합니다.
    auth_instance._session = MagicMock()
    auth_instance._service = 'msi'
    auth_instance._login_failed = False

    # Fetcher의 fetch 메서드가 세션 만료 결과를 반환하도록 모의합니다.
    mock_result = MjuUnivAuthResult(
        request_succeeded=False,
        credentials_valid=False,
        error_code=ErrorCode.SESSION_EXPIRED_ERROR,
        error_message="세션 만료"
    )
    
    # get_student_card 내에서 생성되는 StudentCardFetcher 인스턴스의 fetch 메서드를 패치합니다.
    with patch('mju_univ_auth.facade.StudentCardFetcher') as MockFetcher:
        MockFetcher.return_value.fetch.return_value = mock_result
        result = auth_instance.get_student_card()

    assert not result.success
    assert result.error_code == ErrorCode.SESSION_EXPIRED_ERROR
    assert result.error_message == "세션 만료"
