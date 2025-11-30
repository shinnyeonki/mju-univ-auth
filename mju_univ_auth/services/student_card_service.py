"""
학생카드 조회 서비스
===================
MSI 서비스에서 학생카드 정보를 조회합니다.
"""

import re
from typing import Optional

from ..config.settings import MSIUrls, TIMEOUT_CONFIG
from ..infrastructure.http_client import HTTPClient
from ..infrastructure.parser import HTMLParser
from ..domain.student_card import StudentCard
from ..exceptions import (
    NetworkError,
    PageParsingError,
    InvalidCredentialsError,
    SessionExpiredError,
)
from ..utils import Logger, get_logger


class StudentCardService:
    """학생카드 정보 조회 서비스"""
    
    def __init__(
        self,
        http_client: HTTPClient,
        user_pw: str,
        logger: Optional[Logger] = None,
    ):
        """
        Args:
            http_client: 로그인된 HTTP 클라이언트
            user_pw: 비밀번호 (2차 인증에 사용)
            logger: 로거
        """
        self.http = http_client
        self.user_pw = user_pw
        self.logger = logger or get_logger(False)
        
        self._csrf_token: Optional[str] = None
        self._last_url: Optional[str] = None
    
    def fetch(self) -> StudentCard:
        """
        학생카드 정보를 조회합니다.
        
        Returns:
            StudentCard: 조회된 학생카드 정보
        """
        self.logger.step("A", "학생카드 정보 조회 시작")
        
        # 1. CSRF 토큰 획득
        self._get_csrf_token()
        
        # 2. 학생카드 페이지 접근
        html = self._access_student_card_page()
        
        # 3. 비밀번호 인증 필요 여부 확인 및 처리
        if self._is_password_required(html):
            self.logger.warning("2차 비밀번호 인증이 필요합니다.")
            html = self._submit_password(html)
            html = self._handle_redirect_form(html)
            
            if self._is_password_required(html):
                raise InvalidCredentialsError("2차 비밀번호 인증에 실패했습니다.")
        
        # 4. 학생 정보 파싱
        student_card = self._parse_student_card(html)
        
        self.logger.success("학생카드 정보 조회 완료")
        return student_card
    
    def _get_csrf_token(self) -> None:
        """MSI 홈페이지에서 CSRF 토큰 추출"""
        self.logger.step("A-1", "CSRF 토큰 추출")
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
    
    def _access_student_card_page(self) -> str:
        """학생카드 페이지 접근"""
        self.logger.step("A-2", "학생카드 페이지 접근")
        
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
            'Referer': MSIUrls.HOME,
            'X-CSRF-TOKEN': self._csrf_token,
        }
        
        self.logger.request('POST', MSIUrls.STUDENT_CARD, headers, form_data)
        
        response = self.http.post(
            MSIUrls.STUDENT_CARD,
            data=form_data,
            headers=headers,
            timeout=TIMEOUT_CONFIG.page_access,
        )
        self.logger.response(response, show_body=False)
        
        self._last_url = response.url
        return response.text
    
    def _is_password_required(self, html: str) -> bool:
        """비밀번호 입력이 필요한지 확인"""
        return 'tfpassword' in html or 'verifyPW' in html
    
    def _submit_password(self, html: str) -> str:
        """2차 비밀번호 인증"""
        self.logger.step("A-3", "2차 비밀번호 인증")
        
        # originalurl 추출
        original_match = re.search(r'name="originalurl"\s+value="([^"]+)"', html)
        original_url = original_match.group(1) if original_match else MSIUrls.STUDENT_CARD
        
        form_data = {
            'originalurl': original_url,
            'tfpassword': self.user_pw,
            '_csrf': self._csrf_token,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url or MSIUrls.STUDENT_CARD,
            'X-CSRF-TOKEN': self._csrf_token,
        }
        
        self.logger.request('POST', MSIUrls.PASSWORD_VERIFY, headers, {'originalurl': original_url, 'tfpassword': '****', '_csrf': self._csrf_token})
        
        response = self.http.post(
            MSIUrls.PASSWORD_VERIFY,
            data=form_data,
            headers=headers,
            timeout=TIMEOUT_CONFIG.page_access,
        )
        self.logger.response(response, show_body=True)
        
        self._last_url = response.url
        return response.text
    
    def _handle_redirect_form(self, html: str) -> str:
        """2차 인증 후 리다이렉트 폼 처리"""
        self.logger.step("A-4", "리다이렉트 폼 처리")
        
        action_match = re.search(r'action\s*=\s*["\'](https[^"\']+)["\']', html)
        csrf_match = re.search(r'name=["\']_csrf["\'][^>]*value=["\']([^"]+)["\']', html)
        
        action = action_match.group(1) if action_match else ''
        if not action or 'Sum00Svl01getStdCard' not in action:
            self.logger.warning("리다이렉트 폼을 찾지 못했습니다.")
            return html
        
        csrf = csrf_match.group(1) if csrf_match else self._csrf_token
        
        self.logger.info("Redirect URL", action)
        
        form_data = {'_csrf': csrf}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url,
            'X-CSRF-TOKEN': csrf,
        }
        
        response = self.http.post(action, data=form_data, headers=headers, timeout=TIMEOUT_CONFIG.page_access)
        self.logger.response(response, show_body=False)
        
        return response.text
    
    def _parse_student_card(self, html: str) -> StudentCard:
        """학생카드 HTML 파싱"""
        self.logger.step("A-5", "학생 정보 파싱")
        
        fields = HTMLParser.parse_student_card_fields(html)
        
        if '학번' not in fields or not fields['학번']:
            raise PageParsingError("학생 정보를 찾을 수 없습니다 (학번 필드 누락).", field="student_id")
        
        student_card = StudentCard.from_parsed_fields(fields)
        
        self.logger.success("학생 정보 파싱 완료")
        return student_card
