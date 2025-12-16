from dataclasses import dataclass
from typing import Optional, TypeVar, Generic
from enum import Enum

T = TypeVar('T')

class ErrorCode(str, Enum):
    NONE = ""
    NETWORK_ERROR = "NETWORK_ERROR"
    AUTH_FAILED = "AUTH_FAILED"
    PARSE_ERROR = "PARSE_ERROR"
    SESSION_NOT_EXIST = "SESSION_NOT_EXIST"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SERVICE_INVALID = "SERVICE_INVALID"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    ALREADY_LOGGED_IN = "ALREADY_LOGGED_IN"
    UNKNOWN = "UNKNOWN"

@dataclass
class MjuUnivAuthResult(Generic[T]):
    request_succeeded: bool             # 네트워크, 파싱 등 로직 수행 완료 여부
    credentials_valid: Optional[bool] = None # 아이디/비번 유효성 (로그인 성공 여부)
    data: Optional[T] = None            # 성공 데이터
    error_code: ErrorCode = ErrorCode.NONE
    error_message: str = ""

    @property
    def success(self) -> bool:
        # 로그인 관련 요청이 아니라면(credentials_valid is None), request_succeeded만 본다
        if self.credentials_valid is None:
            return self.request_succeeded
        # 로그인 관련 요청이면 둘 다 성공해야 함
        return self.request_succeeded and self.credentials_valid is True

    def __bool__(self):
        return self.success
