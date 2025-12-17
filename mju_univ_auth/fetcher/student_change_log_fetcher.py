"""
학적변동내역 조회 서비스
========================
MSI 서비스에서 학적변동내역을 조회합니다.
"""

import logging
import requests
from bs4 import BeautifulSoup

from ..fetcher.base_fetcher import BaseFetcher
from ..config import SERVICES, TIMEOUT_CONFIG
from ..infrastructure.parser import HTMLParser
from ..domain.student_changelog import StudentChangeLog, AcademicStatus, ChangeLogEntry
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
        changelog = self._parse_student_changelog(html)

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

    def _parse_student_changelog(self, html: str) -> StudentChangeLog:
        """학적변동내역 HTML 파싱"""
        if self._verbose:
            logger.info("[Step B-3] 학적변동내역 정보 파싱")

        soup = BeautifulSoup(html, 'lxml')
        changelog = StudentChangeLog()
        changelog.raw_data['html'] = html

        # 1. 학적 기본 정보 파싱
        status = AcademicStatus()
        status_table = soup.select_one('.card-item.basic .flex-table')
        if not status_table:
            raise ParsingError("학적 기본 정보 테이블을 찾을 수 없습니다.")

        fields = {}
        for item in status_table.find_all('div', class_='flex-table-item'):
            title = item.find('div', class_='item-title').get_text(strip=True)
            value = item.find('div', class_='item-data').get_text(strip=True)
            fields[title] = value
        
        status.student_id = fields.get('학번', '')
        status.name = fields.get('성명', '')
        status.status = fields.get('학적상태', '')
        status.grade = fields.get('학년', '')
        status.completed_semesters = fields.get('이수학기', '')
        status.department = fields.get('학부(과)', '')
        changelog.academic_status = status

        # 2. 휴학 누적 현황 파싱
        leave_span = soup.select_one('.data-title.small span')
        if leave_span:
            changelog.cumulative_leave_semesters = leave_span.get_text(strip=True)

        # 3. 변동 내역 리스트 파싱
        log_list = []
        log_table = soup.select_one('.read-table table')
        if log_table and log_table.tbody:
            for row in log_table.tbody.find_all('tr'):
                cols = row.find_all('td')
                if len(cols) == 6:
                    entry = ChangeLogEntry(
                        year=cols[0].get_text(strip=True),
                        semester=cols[1].get_text(strip=True),
                        change_type=cols[2].get_text(strip=True),
                        change_date=cols[3].get_text(strip=True),
                        expiry_date=cols[4].get_text(strip=True),
                        reason=cols[5].get_text(strip=True),
                    )
                    log_list.append(entry)
        changelog.change_log_list = log_list

        if not changelog.academic_status.student_id:
            raise ParsingError("학적변동내역 정보를 찾을 수 없습니다 (학번 필드 누락).", field="student_id")

        if self._verbose:
            logger.info("✓ 학적변동내역 정보 파싱 완료")
        return changelog