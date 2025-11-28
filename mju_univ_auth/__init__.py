"""
명지대학교 My iWeb 모듈
=====================
MSI(My iWeb) 서비스에 접속하여 학생 정보를 조회하는 모듈

모듈 구성:
- sso: SSO 로그인 저수준 로직
- student_card: 학생카드 조회 서비스
- student_changelog: 학적변동내역 조회 서비스
- abc: 추상 기본 클래스
- crypto: RSA/AES 암호화 유틸리티
- exceptions: 커스텀 예외 클래스
- utils: 로깅 및 공통 유틸리티
"""

from .student_card import StudentCard
from .student_changelog import StudentChangeLog
from .exceptions import (
    MjuUnivAuthError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError,
    SessionExpiredError
)

__all__ = [
    # 데이터 클래스
    'StudentCard',
    'StudentChangeLog',

    # 예외 클래스
    'MjuUnivAuthError',
    'NetworkError',
    'PageParsingError',
    'InvalidCredentialsError',
    'SessionExpiredError',
]