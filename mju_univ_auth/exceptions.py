"""
myiweb 모듈을 위한 커스텀 예외 클래스
"""

class MyIWebError(Exception):
    """myiweb 모듈의 기본 예외 클래스"""
    pass

class NetworkError(MyIWebError):
    """네트워크 요청 관련 에러"""
    pass

class PageParsingError(MyIWebError):
    """HTML 파싱 관련 에러"""
    pass

class InvalidCredentialsError(MyIWebError):
    """로그인 자격 증명(ID/PW)이 잘못되었을 때 발생하는 에러"""
    pass

class SessionExpiredError(MyIWebError):
    """로그인 세션이 만료되었을 때 발생하는 에러"""
    pass
