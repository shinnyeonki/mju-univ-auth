"""
학생카드 조회 서비스
===================
MSI 서비스에서 학생카드 정보를 조회합니다.
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

from ..fetcher.base_fetcher import BaseFetcher
from ..config import SERVICES, TIMEOUT_CONFIG
from ..infrastructure.parser import HTMLParser
from ..domain.student_card import StudentCard, StudentProfile, PersonalContact, Address
from ..exceptions import (
    NetworkError,
    ParsingError,
    InvalidCredentialsError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)


class StudentCardFetcher(BaseFetcher[StudentCard]):
    """학생카드 정보 조회 서비스"""

    def __init__(
        self,
        session: requests.Session,
        user_pw: str,
        verbose: bool = False,
    ):
        """
        Args:
            session: 로그인된 세션
            user_pw: 비밀번호 (2차 인증에 사용)
            verbose: 상세 로그 출력 여부
        """
        super().__init__(session)
        self.user_pw = user_pw
        self._verbose = verbose

        self._csrf_token: str | None = None
        self._last_url: str | None = None

    def _execute(self) -> StudentCard:
        """
        학생카드 정보를 조회합니다.

        Returns:
            StudentCard: 조회된 학생카드 정보
        """
        if self._verbose:
            logger.info("[Step A] 학생카드 정보 조회 시작")

        # 1. CSRF 토큰 획득
        self._get_csrf_token()

        # 2. 학생카드 페이지 접근
        html = self._access_student_card_page()

        # 3. 비밀번호 인증 필요 여부 확인 및 처리
        if self._is_password_required(html):
            if self._verbose:
                logger.warning("2차 비밀번호 인증이 필요합니다.")
            html = self._submit_password(html)
            html = self._handle_redirect_form(html)

            if self._is_password_required(html):
                raise InvalidCredentialsError("2차 비밀번호 인증에 실패했습니다.")

        # 4. 학생 정보 파싱
        student_card = self._parse_student_card(html)

        if self._verbose:
            logger.info("✓ 학생카드 정보 조회 완료")
        return student_card

    def _get_csrf_token(self) -> None:
        """MSI 홈페이지에서 CSRF 토큰 추출"""
        if self._verbose:
            logger.info("[Step A-1] CSRF 토큰 추출")
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

    def _access_student_card_page(self) -> str:
        """학생카드 페이지 접근"""
        if self._verbose:
            logger.info("[Step A-2] 학생카드 페이지 접근")

        form_data = {
            'sysdiv': 'SCH',
            'subsysdiv': 'SCH',
            'folderdiv': '101',
            'pgmid': 'W_SUD005',
            'userFlag': '1',
            '_csrf': self._csrf_token,
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': SERVICES['msi'].endpoints.HOME,
            'X-CSRF-TOKEN': self._csrf_token,
        }

        if self._verbose:
            logger.debug(f"POST {SERVICES['msi'].endpoints.STUDENT_CARD}")

        try:
            response = self.session.post(
                SERVICES['msi'].endpoints.STUDENT_CARD,
                data=form_data,
                headers=headers,
                timeout=TIMEOUT_CONFIG.page_access,
            )
        except requests.RequestException as e:
            raise NetworkError("학생카드 페이지 접근 실패", url=SERVICES['msi'].endpoints.STUDENT_CARD, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        self._last_url = response.url
        return response.text

    def _is_password_required(self, html: str) -> bool:
        """비밀번호 입력이 필요한지 확인"""
        return 'tfpassword' in html or 'verifyPW' in html

    def _submit_password(self, html: str) -> str:
        """2차 비밀번호 인증"""
        if self._verbose:
            logger.info("[Step A-3] 2차 비밀번호 인증")

        # originalurl 추출
        original_match = re.search(r'name="originalurl"\s+value="([^"]+)"', html)
        original_url = original_match.group(1) if original_match else SERVICES['msi'].endpoints.STUDENT_CARD

        form_data = {
            'originalurl': original_url,
            'tfpassword': self.user_pw,
            '_csrf': self._csrf_token,
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url or SERVICES['msi'].endpoints.STUDENT_CARD,
            'X-CSRF-TOKEN': self._csrf_token,
        }

        if self._verbose:
            logger.debug(f"POST {SERVICES['msi'].endpoints.PASSWORD_VERIFY}")

        try:
            response = self.session.post(
                SERVICES['msi'].endpoints.PASSWORD_VERIFY,
                data=form_data,
                headers=headers,
                timeout=TIMEOUT_CONFIG.page_access,
            )
        except requests.RequestException as e:
            raise NetworkError("비밀번호 인증 요청 실패", url=SERVICES['msi'].endpoints.PASSWORD_VERIFY, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        self._last_url = response.url
        return response.text

    def _handle_redirect_form(self, html: str) -> str:
        """2차 인증 후 리다이렉트 폼 처리"""
        if self._verbose:
            logger.info("[Step A-4] 리다이렉트 폼 처리")

        action_match = re.search(r'action\s*=\s*["\"](https[^"]+)["\"]', html)
        csrf_match = re.search(r'name=["\"]_csrf["\"][^>]*value=["\"]([^"]+)["\"]', html)

        action = action_match.group(1) if action_match else ''
        if not action or 'Sum00Svl01getStdCard' not in action:
            if self._verbose:
                logger.warning("리다이렉트 폼을 찾지 못했습니다.")
            return html

        csrf = csrf_match.group(1) if csrf_match else self._csrf_token

        if self._verbose:
            logger.debug(f"Redirect URL: {action}")

        form_data = {'_csrf': csrf}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url,
            'X-CSRF-TOKEN': csrf,
        }

        try:
            response = self.session.post(action, data=form_data, headers=headers, timeout=TIMEOUT_CONFIG.page_access)
        except requests.RequestException as e:
            raise NetworkError("리다렉트 폼 제출 실패", url=action, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        return response.text

    def _parse_student_card(self, html: str) -> StudentCard:
        """학생카드 HTML 파싱"""
        if self._verbose:
            logger.info("[Step A-5] 학생 정보 파싱")

        soup = BeautifulSoup(html, 'lxml')
        card_item = soup.find('div', class_='card-item basic')
        card = StudentCard()
        card.raw_html_data = str(card_item) if card_item else ''

        # 1. 학생 프로필 정보 파싱
        profile = StudentProfile()
        
        # 사진
        img_tag = soup.select_one('#pictureInclude img')
        if img_tag and 'base64,' in img_tag.get('src', ''):
            profile.photo_base64 = img_tag['src']
            # profile.photo_base64 = img_tag['src'].split('base64,')[1]

        # 기본 정보 테이블
        profile_table = soup.select_one('#pictureInclude .flex-table')
        if not profile_table:
            raise ParsingError("학생 프로필 테이블을 찾을 수 없습니다.")

        fields = {}
        for item in profile_table.find_all('div', class_='flex-table-item'):
            title = item.find('div', class_='item-title').get_text(strip=True)
            value = item.find('div', class_='item-data').get_text(strip=True)
            fields[title] = value
        
        profile.student_id = fields.get('학번', '')
        profile.name_korean = fields.get('한글성명', '')
        profile.grade = fields.get('학년', '').replace('학년', '').strip()
        profile.enrollment_status = fields.get('학적상태', '')
        profile.college_department = fields.get('학부(과)', '')
        profile.academic_advisor = fields.get('상담교수', '')
        advisor_text = fields.get('학생설계전공지도교수', '')
        profile.student_designed_major_advisor = advisor_text.replace('()', '').strip()

        card.student_profile = profile

        # 2. 개인 연락처 정보 파싱
        contact = PersonalContact()
        contact_table = soup.select_one('hr + .flex-table')
        if not contact_table:
            raise ParsingError("개인 연락처 테이블을 찾을 수 없습니다.")

        contact.english_surname = contact_table.find('input', {'name': 'nm_eng'}).get('value', '')
        contact.english_givenname = contact_table.find('input', {'name': 'nm_eng2'}).get('value', '')
        contact.phone_number = contact_table.find('input', {'name': 'std_tel'}).get('value', '')
        contact.mobile_number = contact_table.find('input', {'name': 'htel'}).get('value', '')
        contact.email = contact_table.find('input', {'name': 'email'}).get('value', '')

        # 현거주지 주소
        zip1 = contact_table.find('input', {'name': 'zip1'}).get('value', '')
        zip2 = contact_table.find('input', {'name': 'zip2'}).get('value', '')
        addr1 = contact_table.find('input', {'name': 'addr1'}).get('value', '')
        addr2 = contact_table.find('input', {'name': 'addr2'}).get('value', '')
        contact.current_residence_address = Address(
            postal_code=f"{zip1}-{zip2}",
            address=f"{addr1} {addr2}".strip()
        )

        # 주민등록 주소
        zip1_2 = contact_table.find('input', {'name': 'zip1_2'}).get('value', '')
        zip2_2 = contact_table.find('input', {'name': 'zip2_2'}).get('value', '')
        addr1_2 = contact_table.find('input', {'name': 'addr1_2'}).get('value', '')
        addr2_2 = contact_table.find('input', {'name': 'addr2_2'}).get('value', '')
        contact.resident_registration_address = Address(
            postal_code=f"{zip1_2}-{zip2_2}",
            address=f"{addr1_2} {addr2_2}".strip()
        )
        
        card.personal_contact = contact

        if not card.student_profile.student_id:
            raise ParsingError("학생 정보를 찾을 수 없습니다 (학번 필드 누락).", field="student_id")

        if self._verbose:
            logger.info("✓ 학생 정보 파싱 완료")
        return card