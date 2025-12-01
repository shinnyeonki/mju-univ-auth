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
    final_url: str


# 서비스별 설정
# | 서비스             | 코드명        | 설명               |
# | --------------- | ---------- | ---------------- |
# | 명지대 통합 포털       | `"main"`   | 기본값              |
# | 학사행정시스템 (MSI)   | `"msi"`    | 학생카드, 성적, 수강신청 등 |
# | LMS (LearnUs 등) | `"lms"`    | 강의 자료, 과제        |
# | 캡스톤/현장실습        | `"myicap"` |                  |
# | 인턴십 시스템         | `"intern"` |                  |
# | IPP (산업연계)      | `"ipp"`    |                  |
# | U-CHECK         | `"ucheck"` | 출석 확인            |
# | 포털 (공지/신청)      | `"portal"` |                  |
SERVICES: Dict[str, ServiceConfig] = {
    'main': ServiceConfig(
        name='명지대 통합 포털',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=www&response_type=code&state=1764563970576&rd_c_p=siteId%40%40mjukr%2Credirect_uri%40%40https%253A%252F%252Fwww.mju.ac.kr%252Fmjukr%252Findex.do&redirect_uri=https%3A%2F%2Fwww.mju.ac.kr%2Fsso%2Fauth%2Fresult.do',
        final_url='https://www.mju.ac.kr/mjukr/index.do',
    ),
    'msi': ServiceConfig(
        name='MSI (학사행정시스템)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=msi&response_type=code&state=1764563066913&tkn_type=normal&redirect_uri=https%3A%2F%2Fmsi.mju.ac.kr%2Findex_Myiweb.jsp',
        final_url='https://msi.mju.ac.kr/servlet/security/MySecurityStart',
    ),
    'lms': ServiceConfig(
        name='LMS (LearnUs)',
        auth_url='https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=lms&state=Random%20String&redirect_uri=https://lms.mju.ac.kr/ilos/sso/sso_response.jsp',
        final_url='https://lms.mju.ac.kr/ilos/main/main_form.acl',
    ),
    # 'portal': ServiceConfig(
    #     name='Portal (공지/신청)',
    #     auth_url='https://sso.mju.ac.kr/sso/auth?client_id=portal&response_type=code&state=1764563685370&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fportal.mju.ac.kr%2Fsso%2Fresponse.jsp',
    #     final_url='https://portal.mju.ac.kr/p/S00/',
    # ),
    'myicap': ServiceConfig(
        name='MyiCAP (캡스톤/현장실습)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=myicap&response_type=code&state=1764563719271&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fmyicap.mju.ac.kr%2Findex.jsp',
        final_url='https://myicap.mju.ac.kr/site/main/index001?prevurl=https%3A%2F%2Fsso.mju.ac.kr%2F',
    ),
    'intern': ServiceConfig(
        name='인턴십 시스템',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=intern&response_type=code&state=1764563776458&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fintern.mju.ac.kr%2Fsso.do',
        final_url='https://intern.mju.ac.kr/main.do',
    ),
    'ipp': ServiceConfig(
        name='IPP (산업연계)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=ipp&response_type=code&state=1764563932107&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fipp.mju.ac.kr%2Findex.do',
        final_url='https://ipp.mju.ac.kr/common/common.do?jsp_path=index',
    ),
    'ucheck': ServiceConfig(
        name='U-CHECK (출석확인)',
        auth_url='https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=ucheck&state=sso-1764564022377&redirect_uri=https%3A%2F%2Fucheck.mju.ac.kr',
        final_url='https://ucheck.mju.ac.kr/',
    ),
}


# MSI 서비스 URL 설정
class MSIUrls:
    """MSI 서비스의 URL 정의"""
    BASE = "https://msi.mju.ac.kr"
    HOME = "https://msi.mju.ac.kr/servlet/security/MySecurityStart"
    STUDENT_CARD = "https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard"
    PASSWORD_VERIFY = "https://msi.mju.ac.kr/servlet/sys/sys15/Sys15Svl01verifyPW"
    CHANGE_LOG = "https://msi.mju.ac.kr/servlet/su/sud/Sud00Svl03viewChangeLog"


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

