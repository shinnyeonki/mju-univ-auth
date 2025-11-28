"""
MjuUnivAuth 모듈을 위한 커스텀 예외 클래스
"""

class MjuUnivAuthError(Exception):
    """MjuUnivAuth 모듈의 기본 예외 클래스"""
    pass

class NetworkError(MjuUnivAuthError):
    """네트워크 요청 관련 에러"""
    pass

class PageParsingError(MjuUnivAuthError):
    """HTML 파싱 관련 에러"""
    pass

class InvalidCredentialsError(MjuUnivAuthError):
    """로그인 자격 증명(ID/PW)이 잘못되었을 때 발생하는 에러"""
    pass

class SessionExpiredError(MjuUnivAuthError):
    """로그인 세션이 만료되었을 때 발생하는 에러"""
    pass
