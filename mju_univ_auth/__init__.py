"""
명지대학교 My iWeb 모듈
=====================
MSI(My iWeb) 서비스에 접속하여 학생 정보를 조회하는 모듈

사용법:
    from mju_univ_auth import MjuUnivAuth
    
    auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
    student_card = auth.get_student_card()
    print(student_card.name_korean)

모듈 구성:
- facade: MjuUnivAuth - 메인 API 클래스
- domain: StudentCard, StudentChangeLog - 데이터 모델
- base: Authenticator, BaseFetcher - 기반 클래스
- config: 서비스 설정
- utils: 로깅 유틸리티
- exceptions: 커스텀 예외 클래스
"""

# 메인 Facade 클래스
from .facade import MjuUnivAuth

# 기반 클래스
from .Authenticator import Authenticator
from .base_fetcher import BaseFetcher

# Fetcher 클래스
from .student_card_fetcher import StudentCardFetcher
from .student_change_log_fetcher import StudentChangeLogFetcher

# 도메인 모델
from .domain import StudentCard, StudentChangeLog

# 결과 객체
from .results import MjuUnivAuthResult, ErrorCode

# 예외 클래스
from .exceptions import (
    MjuUnivAuthError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError,
    SessionExpiredError,
    ServiceNotFoundError,
)

__all__ = [
    # 메인 API
    'MjuUnivAuth',
    
    # 기반 클래스
    'Authenticator',
    'BaseFetcher',
    
    # Fetcher 클래스
    'StudentCardFetcher',
    'StudentChangeLogFetcher',
    
    # 데이터 클래스
    'StudentCard',
    'StudentChangeLog',

    # 결과 객체
    'MjuUnivAuthResult',
    'ErrorCode',

    # 예외 클래스
    'MjuUnivAuthError',
    'NetworkError',
    'PageParsingError',
    'InvalidCredentialsError',
    'SessionExpiredError',
    'ServiceNotFoundError',
]

__version__ = '0.5.0'
