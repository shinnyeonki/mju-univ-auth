"""
학적변동내역 조회 서비스
========================
MSI 서비스에서 학적변동내역을 조회합니다.
"""

from typing import Optional

from ..config.settings import MSIUrls, TIMEOUT_CONFIG
from ..infrastructure.http_client import HTTPClient
from ..infrastructure.parser import HTMLParser
from ..domain.student_changelog import StudentChangeLog
from ..exceptions import (
    PageParsingError,
    SessionExpiredError,
)
from ..utils import Logger, get_logger


class StudentChangeLogService:
    """학적변동내역 조회 서비스"""
    
    def __init__(
        self,
        http_client: HTTPClient,
        logger: Optional[Logger] = None,
    ):
        """
        Args:
            http_client: 로그인된 HTTP 클라이언트
            logger: 로거
        """
        self.http = http_client
        self.logger = logger or get_logger(False)
        
        self._csrf_token: Optional[str] = None
    
    def fetch(self) -> StudentChangeLog:
        """
        학적변동내역을 조회합니다.
        
        Returns:
            StudentChangeLog: 조회된 학적변동내역 정보
        """
        self.logger.step("B", "학적변동내역 정보 조회 시작")
        
        # 1. CSRF 토큰 획득
        self._get_csrf_token()
        
        # 2. 학적변동내역 페이지 접근
        html = self._access_changelog_page()
        
        # 3. 정보 파싱
        changelog = self._parse_changelog(html)
        
        self.logger.success("학적변동내역 정보 조회 완료")
        return changelog
    
    def _get_csrf_token(self) -> None:
        """MSI 홈페이지에서 CSRF 토큰 추출"""
        self.logger.step("B-1", "CSRF 토큰 추출")
        self.logger.request('GET', MSIUrls.HOME)
        
        response = self.http.get(MSIUrls.HOME, timeout=TIMEOUT_CONFIG.default)
        self.logger.response(response, show_body=False)
        
        # 세션 만료 확인
        if 'sso.mju.ac.kr' in response.url:
            raise SessionExpiredError("세션이 만료되었습니다. 다시 로그인해주세요.", redirect_url=response.url)
        
        self._csrf_token = HTMLParser.extract_csrf_token(response.text)
        
        if not self._csrf_token:
            raise PageParsingError("CSRF 토큰을 찾을 수 없습니다.", field="csrf")
        
        self.logger.info("CSRF Token", self._csrf_token)
        self.logger.success("CSRF 토큰 추출 완료")
    
    def _access_changelog_page(self) -> str:
        """학적변동내역 페이지 접근"""
        self.logger.step("B-2", "학적변동내역 페이지 접근")
        
        full_url = f"https://msi.mju.ac.kr{MSIUrls.CHANGE_LOG}"
        
        form_data = {
            'sysdiv': 'SCH',
            'subsysdiv': 'SCH',
            'folderdiv': '101',
            'pgmid': 'W_SUD020',
            '_csrf': self._csrf_token,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': MSIUrls.HOME,
            'X-CSRF-TOKEN': self._csrf_token,
        }
        
        self.logger.request('POST', full_url, headers, form_data)
        
        response = self.http.post(
            full_url,
            data=form_data,
            headers=headers,
            timeout=TIMEOUT_CONFIG.page_access,
        )
        self.logger.response(response, show_body=False)
        
        return response.text
    
    def _parse_changelog(self, html: str) -> StudentChangeLog:
        """학적변동내역 HTML 파싱"""
        self.logger.step("B-3", "학적변동내역 정보 파싱")
        
        fields = HTMLParser.parse_change_log_fields(html)
        
        if '학번' not in fields or not fields['학번']:
            raise PageParsingError("학적변동내역 정보를 찾을 수 없습니다 (학번 필드 누락).", field="student_id")
        
        changelog = StudentChangeLog.from_parsed_fields(fields)
        
        self.logger.success("학적변동내역 정보 파싱 완료")
        return changelog
