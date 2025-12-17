"""
학생 기본 정보 조회 서비스
=========================
MSI 메인 페이지에서 대시보드 요약 정보를 조회합니다.
"""

import logging
import requests
from bs4 import BeautifulSoup

from ..fetcher.base_fetcher import BaseFetcher
from ..config import SERVICES, TIMEOUT_CONFIG
from ..domain.student_basicinfo import StudentBasicInfo
from ..exceptions import (
    NetworkError,
    ParsingError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)


class StudentBasicInfoFetcher(BaseFetcher[StudentBasicInfo]):
    """학생 기본 정보(대시보드 요약) 조회 서비스"""

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

    def _execute(self) -> StudentBasicInfo:
        """
        학생 기본 정보를 조회합니다.

        Returns:
            StudentBasicInfo: 조회된 학생 기본 정보
        """
        if self._verbose:
            logger.info("[Step C] 학생 기본 정보 조회 시작")

        # 1. MSI 메인 페이지 접근
        html = self._access_main_page()

        # 2. 정보 파싱
        basic_info = self._parse_basic_info(html)

        if self._verbose:
            logger.info("✓ 학생 기본 정보 조회 완료")
        return basic_info

    def _access_main_page(self) -> str:
        """MSI 메인 페이지(MySecurityStart) 접근"""
        if self._verbose:
            logger.info("[Step C-1] MSI 메인 페이지 접근")
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

        return response.text

    def _parse_basic_info(self, html: str) -> StudentBasicInfo:
        """학생 기본 정보 HTML 파싱"""
        if self._verbose:
            logger.info("[Step C-2] 학생 기본 정보 파싱")

        soup = BeautifulSoup(html, 'lxml')
        info_card = soup.find('div', class_='main-user-info')

        if not info_card:
            raise ParsingError("기본 정보 카드('main-user-info')를 찾을 수 없습니다.")

        info = StudentBasicInfo()
        info.raw_data['html'] = str(info_card)

        info_cells = info_card.find_all('div', class_='info-cell')
        data = {}
        for cell in info_cells:
            title = cell.find('div', class_='title').get_text(strip=True).replace(':', '').strip()
            value = cell.find('div', class_='value').get_text(strip=True)
            data[title] = value

        info.department = data.get('소 속', '')
        info.category = data.get('구 분', '')
        info.grade = data.get('학 년', '')
        info.last_access_time = data.get('최근접속시간', '')
        info.last_access_ip = data.get('최근접속IP', '')
        
        if not info.department:
            raise ParsingError("기본 정보 필드('소속')를 파싱할 수 없습니다.")

        if self._verbose:
            logger.info("✓ 학생 기본 정보 파싱 완료")
        return info
