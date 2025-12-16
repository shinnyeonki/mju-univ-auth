"""
학적변동내역 조회 서비스
========================
MSI 서비스에서 학적변동내역을 조회합니다.
"""

import logging
import requests

from ..fetcher.base_fetcher import BaseFetcher
from ..config import SERVICES, TIMEOUT_CONFIG
from ..infrastructure.parser import HTMLParser
from ..domain.student_changelog import StudentChangeLog
from ..exceptions import (
    NetworkError,
    ParsingError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)


class StudentChangeLogFetcher(BaseFetcher[StudentChangeLog]):
    """학적변동내역 조회 서비스"""

    def __init__(
        self,
        session: requests.Session,
        verbose: bool = False,
    ):
        """
        Args:
            session: 로그인된 세션
            verbose: 상세 로그 출력 여부
        """
        super().__init__(session)
        self._verbose = verbose

        self._csrf_token: str | None = None

    def _execute(self) -> StudentChangeLog:
        """
        학적변동내역을 조회합니다.

        Returns:
            StudentChangeLog: 조회된 학적변동내역 정보
        """
        if self._verbose:
            logger.info("[Step B] 학적변동내역 정보 조회 시작")

        # 1. CSRF 토큰 획득
        self._get_csrf_token()

        # 2. 학적변동내역 페이지 접근
        html = self._access_changelog_page()

        # 3. 정보 파싱
        changelog = self._parse_changelog(html)

        if self._verbose:
            logger.info("✓ 학적변동내역 정보 조회 완료")
        return changelog

    def _get_csrf_token(self) -> None:
        """MSI 홈페이지에서 CSRF 토큰 추출"""
        if self._verbose:
            logger.info("[Step B-1] CSRF 토큰 추출")
            logger.debug(f"GET {SERVICES['msi'].endpoints.HOME}")

        try:
            response = self.session.get(SERVICES['msi'].endpoints.HOME, timeout=TIMEOUT_CONFIG.default)
        except requests.RequestException as e:
            raise NetworkError("MSI 홈페이지 접속 실패", url=SERVICES['msi'].endpoints.HOME, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        # 세션 만료 확인
        if 'sso.mju.ac.kr' in response.url:
            raise SessionExpiredError("세션이 만료되었습니다. 다시 로그인해주세요.", redirect_url=response.url)

        self._csrf_token = HTMLParser.extract_csrf_token(response.text)

        if not self._csrf_token:
            raise ParsingError("CSRF 토큰을 찾을 수 없습니다.", field="csrf")

        if self._verbose:
            logger.debug(f"CSRF Token: {self._csrf_token}")
            logger.info("✓ CSRF 토큰 추출 완료")

    def _access_changelog_page(self) -> str:
        """학적변동내역 페이지 접근"""
        if self._verbose:
            logger.info("[Step B-2] 학적변동내역 페이지 접근")

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
            'Referer': SERVICES['msi'].endpoints.HOME,
            'X-CSRF-TOKEN': self._csrf_token,
        }

        if self._verbose:
            logger.debug(f"POST {SERVICES['msi'].endpoints.CHANGE_LOG}")

        try:
            response = self.session.post(
                SERVICES['msi'].endpoints.CHANGE_LOG,
                data=form_data,
                headers=headers,
                timeout=TIMEOUT_CONFIG.page_access,
            )
        except requests.RequestException as e:
            raise NetworkError("학적변동내역 페이지 접근 실패", url=SERVICES['msi'].endpoints.CHANGE_LOG, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        return response.text

    def _parse_changelog(self, html: str) -> StudentChangeLog:
        """학적변동내역 HTML 파싱"""
        if self._verbose:
            logger.info("[Step B-3] 학적변동내역 정보 파싱")

        fields = HTMLParser.parse_change_log_fields(html)

        if '학번' not in fields or not fields['학번']:
            raise ParsingError("학적변동내역 정보를 찾을 수 없습니다 (학번 필드 누락).", field="student_id")

        changelog = StudentChangeLog.from_parsed_fields(fields)

        if self._verbose:
            logger.info("✓ 학적변동내역 정보 파싱 완료")
        return changelog
