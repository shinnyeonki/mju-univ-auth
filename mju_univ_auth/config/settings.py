"""
설정 관리 모듈
==============
서비스별 URL, 도메인, 기본 설정 등을 집중 관리합니다.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ServiceConfig:
    """서비스별 설정 데이터 클래스"""
    name: str
    auth_url: str
    success_domain: str
    test_url: str


# 서비스별 설정
SERVICES: Dict[str, ServiceConfig] = {
    'lms': ServiceConfig(
        name='LMS (e-Class)',
        auth_url='https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=lms&state=Random%20String&redirect_uri=https://lms.mju.ac.kr/ilos/sso/sso_response.jsp',
        success_domain='lms.mju.ac.kr',
        test_url='https://lms.mju.ac.kr/ilos/main/main_form.acl'
    ),
    'portal': ServiceConfig(
        name='Portal (통합정보시스템)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=portal&response_type=code&state=1764321341781&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fportal.mju.ac.kr%2Fsso%2Fresponse.jsp',
        success_domain='portal.mju.ac.kr',
        test_url='https://portal.mju.ac.kr/portal/main.do'
    ),
    'library': ServiceConfig(
        name='Library (도서관)',
        auth_url='https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=library&state=state&redirect_uri=https://lib.mju.ac.kr/sso/login',
        success_domain='lib.mju.ac.kr',
        test_url='https://lib.mju.ac.kr/main'
    ),
    'msi': ServiceConfig(
        name='MSI (My iWeb)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=msi&response_type=code&state=1764322070097&tkn_type=normal&redirect_uri=https%3A%2F%2Fmsi.mju.ac.kr%2Findex_Myiweb.jsp',
        success_domain='msi.mju.ac.kr',
        test_url='https://msi.mju.ac.kr/index_Myiweb.jsp'
    ),
    'myicap': ServiceConfig(
        name='MyiCAP (비교과)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=myicap&response_type=code&state=1764322418883&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fmyicap.mju.ac.kr%2Findex.jsp',
        success_domain='myicap.mju.ac.kr',
        test_url='https://myicap.mju.ac.kr/index.jsp'
    ),
}


# MSI 서비스 URL 설정
class MSIUrls:
    """MSI 서비스의 URL 정의"""
    HOME = "https://msi.mju.ac.kr/servlet/security/MySecurityStart"
    STUDENT_CARD = "https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard"
    PASSWORD_VERIFY = "https://msi.mju.ac.kr/servlet/sys/sys15/Sys15Svl01verifyPW"
    CHANGE_LOG = "/servlet/su/sud/Sud00Svl03viewChangeLog"


# HTTP 기본 설정
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}


@dataclass(frozen=True)
class TimeoutConfig:
    """타임아웃 설정"""
    default: int = 10
    login: int = 15
    page_access: int = 15


TIMEOUT_CONFIG = TimeoutConfig()
