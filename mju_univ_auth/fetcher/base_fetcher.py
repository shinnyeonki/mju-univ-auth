"""
기반 Fetcher 클래스 모듈
=======================
데이터 조회를 위한 BaseFetcher 기반 클래스를 정의합니다.
"""

from typing import Generic, TypeVar
import requests

from ..results import MjuUnivAuthResult, ErrorCode
from ..exceptions import (
    NetworkError,
    ParsingError,
    InvalidCredentialsError,
    SessionExpiredError,
    SessionNotExistError,
)

T = TypeVar('T')


class BaseFetcher(Generic[T]):
    """데이터 조회를 위한 기반 클래스"""
    
    def __init__(self, session: requests.Session):
        self.session = session

    def fetch(self) -> MjuUnivAuthResult[T]:
        if self.session is None:
            try:
                raise SessionNotExistError()
            except SessionNotExistError as e:
                return MjuUnivAuthResult(
                    request_succeeded=False,
                    credentials_valid=False,
                    error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                    error_message=str(e)
                )

        try:
            data = self._execute()
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=True,
                data=data
            )
            
        except ParsingError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=True,
                error_code=ErrorCode.PARSING_ERROR,
                error_message=str(e)
            )
            
        except NetworkError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=None,
                error_code=ErrorCode.NETWORK_ERROR,
                error_message=str(e)
            )
            
        except SessionExpiredError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.SESSION_EXPIRED_ERROR,
                error_message=str(e)
            )

        except InvalidCredentialsError as e:
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=False,
                error_code=ErrorCode.INVALID_CREDENTIALS_ERROR,
                error_message=str(e),
            )

        except Exception as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=None,
                error_code=ErrorCode.UNKNOWN_ERROR,
                error_message=str(e)
            )

    def _execute(self) -> T:
        """자식 클래스 구현부: 실패 시 반드시 커스텀 예외를 raise 해야 함"""
        raise NotImplementedError
