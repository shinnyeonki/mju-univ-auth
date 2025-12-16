"""
MjuUnivAuth 모듈을 위한 커스텀 예외 클래스
==========================================
모든 예외에 context 정보를 추가하여 디버깅을 용이하게 합니다.
"""

from typing import Optional


class MjuUnivAuthError(Exception):
    """MjuUnivAuth 모듈의 기본 예외 클래스"""
    
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.message = message
        self.context = context
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class NetworkError(MjuUnivAuthError):
    """네트워크 요청 관련 에러"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
        **context
    ):
        super().__init__(message, **context)
        self.url = url
        self.status_code = status_code
        self.original_error = original_error
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.url:
            parts.append(f"url={self.url}")
        if self.status_code:
            parts.append(f"status={self.status_code}")
        if self.context:
            parts.extend(f"{k}={v}" for k, v in self.context.items())
        return " [".join([parts[0], ", ".join(parts[1:]) + "]"]) if len(parts) > 1 else parts[0]


class ParsingError(MjuUnivAuthError):
    """HTML 등 페이지 파싱 관련 에러"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        url: Optional[str] = None,
        **context
    ):
        super().__init__(message, **context)
        self.field = field
        self.url = url


class InvalidCredentialsError(MjuUnivAuthError):
    """로그인 자격 증명(ID/PW)이 잘못되었을 때 발생하는 에러"""
    
    def __init__(
        self,
        message: str = "인증 실패",
        service: Optional[str] = None,
        **context
    ):
        super().__init__(message, **context)
        self.service = service


class SessionExpiredError(MjuUnivAuthError):
    """로그인 세션이 만료되었을 때 발생하는 에러"""
    
    def __init__(
        self,
        message: str = "세션이 만료되었습니다",
        redirect_url: Optional[str] = None,
        **context
    ):
        super().__init__(message, **context)
        self.redirect_url = redirect_url


class SessionNotExistError(MjuUnivAuthError):
    """로그인 세션이 존재하지 않을 때 발생하는 에러"""
    
    def __init__(
        self,
        message: str = "세션이 존재하지 않습니다. 먼저 로그인을 수행해야 합니다.",
        **context
    ):
        super().__init__(message, **context)


class AlreadyLoggedInError(MjuUnivAuthError):
    """이미 로그인된 상태에서 다시 로그인을 시도할 때 발생하는 에러"""
    
    def __init__(
        self,
        message: str = "이미 로그인된 세션입니다.",
        **context
    ):
        super().__init__(message, **context)


class ServiceNotFoundError(MjuUnivAuthError):
    """요청한 서비스를 찾을 수 없을 때 발생하는 에러"""
    
    def __init__(
        self,
        service: str,
        available_services: Optional[list] = None,
        **context
    ):
        message = f"알 수 없는 서비스: {service}"
        if available_services:
            message += f" (사용 가능: {', '.join(available_services)})"
        super().__init__(message, **context)
        self.service = service
        self.available_services = available_services


class InvalidServiceUsageError(MjuUnivAuthError):
    """해당 서비스에서 지원하지 않는 기능을 호출했을 때 발생하는 에러"""

    def __init__(
        self,
        message: str,
        service: str,
        **context
    ):
        super().__init__(message, **context)
        self.service = service
