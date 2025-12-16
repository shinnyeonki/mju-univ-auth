"""
기반 Authenticator 클래스 모듈
=============================
인증을 위한 BaseAuthenticator 기반 클래스를 정의합니다.
"""
from typing import Optional
import requests

from ..results import MjuUnivAuthResult, ErrorCode
from ..exceptions import (
    MjuUnivAuthError,
    InvalidCredentialsError,
    NetworkError,
    ServiceNotFoundError,
    ParsingError,
    SessionExpiredError,
    AlreadyLoggedInError,
    InvalidServiceUsageError,
)


class BaseAuthenticator:
    """인증을 위한 기반 클래스"""

    def __init__(
        self,
        user_id: str,
        user_pw: str,
        verbose: bool = False,
    ):
        """
        Args:
            user_id: 학번/교번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부
        """
        self._user_id = user_id
        self._user_pw = user_pw
        self._verbose = verbose
        self._session: Optional[requests.Session] = None
        self._service: Optional[str] = None

    def login(self, service: str = 'msi') -> MjuUnivAuthResult[requests.Session]:
        """
        SSO 로그인 수행

        Args:
            service: 로그인할 서비스 (기본값: 'msi')

        Returns:
            MjuUnivAuthResult[requests.Session]: 로그인 결과
        """
        session = requests.Session()
        try:
            self._execute_login(session, service)
            self._service = service

            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=True,
                data=session
            )

        except InvalidCredentialsError as e:
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=False,
                error_code=ErrorCode.INVALID_CREDENTIALS_ERROR,
                error_message=str(e)
            )
        except NetworkError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.NETWORK_ERROR,
                error_message=str(e)
            )
        except ServiceNotFoundError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.SERVICE_NOT_FOUND_ERROR,
                error_message=str(e)
            )
        except ParsingError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=True,
                error_code=ErrorCode.PARSING_ERROR,
                error_message=str(e)
            )
        except SessionExpiredError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=True,
                error_code=ErrorCode.SESSION_EXPIRED_ERROR,
                error_message=str(e)
            )
        except AlreadyLoggedInError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=True,
                error_code=ErrorCode.ALREADY_LOGGED_IN_ERROR,
                error_message=str(e)
            )
        except InvalidServiceUsageError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.SERVICE_UNKNOWN_ERROR,
                error_message=str(e)
            )
        except Exception as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=str(e)
            )

    def _execute_login(self, session: requests.Session, service: str):
        """자식 클래스 구현부: 실패 시 반드시 커스텀 예외를 raise 해야 함"""
        raise NotImplementedError

    def is_session_valid(self, service: str = 'msi') -> bool:
        """
        현재 세션이 유효한지 확인합니다.
        자식 클래스에서 구현해야 합니다.

        Args:
            service: 확인할 서비스 (기본값: 'msi')

        Returns:
            bool: 세션 유효 여부
        """
        raise NotImplementedError

    @property
    def session(self) -> Optional[requests.Session]:
        """
        현재 로그인된 `requests.Session` 객체를 반환합니다.
        로그인되지 않은 경우 `None`을 반환합니다.
        """
        return self._session

    @property
    def service(self) -> Optional[str]:
        """
        로그인에 성공한 서비스의 이름을 반환합니다.
        로그인되지 않은 경우 `None`을 반환합니다.
        """
        return self._service
