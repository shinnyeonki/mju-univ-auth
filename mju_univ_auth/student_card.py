
"""
학생카드 정보 조회 모듈
=======================
MSI 서비스에서 학생카드 정보를 조회하고 파싱합니다.
2차 비밀번호 인증을 포함하는 복잡한 조회 과정을 처리합니다.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup, SoupStrainer

from .abc import BaseFetcher
from .utils import (
    Colors, log_section, log_step, log_info, log_success, log_error,
    log_warning, log_request, log_response
)
from .exceptions import (
    MjuUnivAuthError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError
)


@dataclass
class StudentCard:
    """학생카드 정보 데이터 클래스"""
    # 기본 정보
    student_id: str = ""           # 학번
    name_korean: str = ""          # 한글성명
    name_english_first: str = ""   # 영문성명(성)
    name_english_last: str = ""    # 영문성명(이름)
    
    # 학적 정보
    grade: str = ""                # 학년
    status: str = ""               # 학적상태 (재학, 휴학 등)
    department: str = ""           # 학부(과)
    advisor: str = ""              # 상담교수
    design_advisor: str = ""       # 학생설계전공지도교수
    
    # 연락처 정보
    phone: str = ""                # 전화번호
    mobile: str = ""               # 휴대폰
    email: str = ""                # 이메일
    
    # 주소 정보
    current_zip: str = ""          # 현거주지 우편번호
    current_address1: str = ""     # 현거주지 주소1
    current_address2: str = ""     # 현거주지 주소2
    registered_zip: str = ""       # 주민등록 우편번호
    registered_address1: str = ""  # 주민등록 주소1
    registered_address2: str = ""  # 주민등록 주소2
    
    # 사진 (Base64)
    photo_base64: str = ""
    
    # 기타
    focus_newsletter: bool = False  # 명지포커스 수신여부
    
    # 원본 데이터 (딕셔너리)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def fetch(cls, user_id: str, user_pw: str, verbose: bool = False) -> StudentCard:
        """
        SSO 로그인부터 학생카드 정보 조회까지 모든 과정을 수행합니다.

        Args:
            user_id: 학번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부

        Returns:
            조회된 학생카드 정보 객체
        """
        # 순환 참조 방지를 위해 메서드 내에서 임포트
        from .sso import MJUSSOLogin

        if verbose:
            log_section("mju-univ-auth 통합 실행: 학생카드")

        sso = MJUSSOLogin(user_id, user_pw, verbose=verbose)
        session = sso.login(service='msi')

        fetcher = _StudentCardFetcher(session, user_pw, verbose=verbose)
        return fetcher.fetch()

    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 명시적인 딕셔너리로 변환합니다."""
        return {
            'student_id': self.student_id,
            'name_korean': self.name_korean,
            'name_english': f"{self.name_english_first} {self.name_english_last}".strip(),
            'grade': self.grade,
            'status': self.status,
            'department': self.department,
            'advisor': self.advisor,
            'design_advisor': self.design_advisor,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email,
            'current_address': f"({self.current_zip}) {self.current_address1} {self.current_address2}".strip(),
            'registered_address': f"({self.registered_zip}) {self.registered_address1} {self.registered_address2}".strip(),
            'photo_base64': self.photo_base64,
            'focus_newsletter': self.focus_newsletter,
        }

    def print_summary(self) -> None:
        """학생 정보 요약 출력"""
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f" 학생카드 정보 조회 결과")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}")
        
        print(f"\n{Colors.BOLD}[기본 정보]{Colors.END}")
        log_info("학번", self.student_id)
        log_info("한글성명", self.name_korean)
        log_info("영문성명", f"{self.name_english_first} {self.name_english_last}")
        
        print(f"\n{Colors.BOLD}[학적 정보]{Colors.END}")
        log_info("학년", self.grade)
        log_info("학적상태", self.status)
        log_info("학부(과)", self.department)
        log_info("상담교수", self.advisor)
        if self.design_advisor:
            log_info("학생설계전공지도교수", self.design_advisor)
        
        print(f"\n{Colors.BOLD}[연락처]{Colors.END}")
        log_info("전화번호", self.phone)
        log_info("휴대폰", self.mobile)
        log_info("E-Mail", self.email)
        
        print(f"\n{Colors.BOLD}[주소]{Colors.END}")
        log_info("현거주지", f"({self.current_zip}) {self.current_address1} {self.current_address2}")
        log_info("주민등록", f"({self.registered_zip}) {self.registered_address1} {self.registered_address2}")
        
        if self.photo_base64:
            print(f"\n{Colors.BOLD}[사진]{Colors.END}")
            log_info("사진 데이터", f"Base64 ({len(self.photo_base64)} chars)")
            print("사진 미리보기", self.photo_base64)


class _StudentCardFetcher(BaseFetcher):
    """학생카드 정보 조회 서비스 (내부용)"""
    
    STUDENT_CARD_URL = "https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard"
    PASSWORD_VERIFY_URL = "https://msi.mju.ac.kr/servlet/sys/sys15/Sys15Svl01verifyPW"
    
    def __init__(self, session: requests.Session, user_pw: str, verbose: bool = True):
        super().__init__(session, user_pw, verbose)

    def fetch(self) -> StudentCard:
        """학생카드 정보를 조회합니다."""
        if self.verbose:
            log_step("A", "학생카드 정보 조회 시작")
        
        # 1. CSRF 토큰 추출 (from BaseFetcher)
        self._get_csrf_token()
        
        # 2. 학생카드 페이지 접근 (sideform 방식)
        html = self._access_student_card_page()
        
        # 3. 비밀번호 인증 필요 여부 확인 및 처리
        if self._is_password_required(html):
            if self.verbose:
                log_warning("2차 비밀번호 인증이 필요합니다.")
            
            # 비밀번호 제출
            html = self._submit_password(html)
            
            # 리다이렉트 폼 처리
            html = self._handle_redirect_form(html)
            
            # 여전히 비밀번호 인증이 필요하면 실패
            if self._is_password_required(html):
                raise InvalidCredentialsError("2차 비밀번호 인증에 실패했습니다.")
        
        # 4. 최종 학생 정보 파싱
        info = self._parse_info(html)
        
        if self.verbose:
            log_success("학생카드 정보 조회 완료")
            info.print_summary()
            
        return info

    def _access_student_card_page(self) -> str:
        """sideform 방식으로 학생카드 페이지 접근"""
        if self.verbose:
            log_step("A-2", "학생카드 페이지 접근")
        
        form_data = {
            'sysdiv': 'SCH',
            'subsysdiv': 'SCH',
            'folderdiv': '101',
            'pgmid': 'W_SUD005',
            'userFlag': '1',
            '_csrf': self.csrf_token,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self.MSI_HOME_URL,
            'X-CSRF-TOKEN': self.csrf_token,
        }
        
        if self.verbose:
            log_request('POST', self.STUDENT_CARD_URL, headers, form_data)
        
        try:
            response = self.session.post(
                self.STUDENT_CARD_URL,
                data=form_data,
                headers=headers,
                timeout=15
            )
            if self.verbose:
                log_response(response, show_body=False)
            self._last_url = response.url
            return response.text
        except requests.RequestException as e:
            raise NetworkError(f"학생카드 페이지 접근 실패: {e}") from e
    
    def _is_password_required(self, html: str) -> bool:
        """비밀번호 입력이 필요한지 확인"""
        return 'tfpassword' in html or 'verifyPW' in html
    
    def _submit_password(self, html: str) -> str:
        """비밀번호를 제출하여 2차 인증을 수행합니다."""
        if self.verbose:
            log_step("A-3", "2차 비밀번호 인증")
        
        original_match = re.search(r'name="originalurl"\s+value="([^"]+)"', html)
        original_url = original_match.group(1) if original_match else self.STUDENT_CARD_URL
        
        form_data = {
            'originalurl': original_url,
            'tfpassword': self.user_pw,
            '_csrf': self.csrf_token,
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url or self.STUDENT_CARD_URL,
            'X-CSRF-TOKEN': self.csrf_token,
        }
        
        if self.verbose:
            safe_data = {k: ('****' if 'password' in k.lower() else v) for k, v in form_data.items()}
            log_request('POST', self.PASSWORD_VERIFY_URL, headers, safe_data)
        
        try:
            response = self.session.post(
                self.PASSWORD_VERIFY_URL,
                data=form_data,
                headers=headers,
                timeout=15
            )
            if self.verbose:
                log_response(response, show_body=True)
            self._last_url = response.url
            return response.text
        except requests.RequestException as e:
            raise NetworkError(f"비밀번호 인증 실패: {e}") from e
    
    def _handle_redirect_form(self, html: str) -> str:
        """2차 인증 후 나타나는 JS 리다이렉트 폼을 처리합니다."""
        if self.verbose:
            log_step("A-4", "리다이렉트 폼 처리")

        # 더 간단하고 정확한 정규표현식으로 수정
        action_match = re.search(r'action\s*=\s*["\"](https[^"\"]+)["\"]', html)
        csrf_match = re.search(r'name=["\"]_csrf["\"][^>]*value=["\"]([^"]+)["\"]', html)

        action = action_match.group(1) if action_match else ''
        if not action or 'Sum00Svl01getStdCard' not in action:
            if self.verbose:
                log_warning("리다이렉트 폼을 찾지 못했습니다. 현재 HTML을 그대로 반환합니다.")
            return html
        
        csrf = csrf_match.group(1) if csrf_match else self.csrf_token
        
        if self.verbose:
            log_info("Redirect URL", action)
            log_info("CSRF Token", csrf)
        
        form_data = {'_csrf': csrf}
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self._last_url,
            'X-CSRF-TOKEN': csrf,
        }
        
        try:
            response = self.session.post(action, data=form_data, headers=headers, timeout=15)
            if self.verbose:
                log_response(response, show_body=False)
            return response.text
        except requests.RequestException as e:
            raise NetworkError(f"리다이렉트 폼 처리 실패: {e}") from e
    
    def _parse_info(self, html: str) -> StudentCard:
        """학생 정보 HTML을 파싱합니다."""
        if self.verbose:
            log_step("A-5", "학생 정보 파싱")
        
        parse_only = SoupStrainer(['img', 'div', 'input'])
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        info = StudentCard()
        
        img_tag = soup.find('img', src=re.compile(r'^data:image'))
        if img_tag:
            src = img_tag.get('src', '')
            if 'base64,' in src:
                info.photo_base64 = src.split('base64,')[1]
        
        for item in soup.find_all('div', class_='flex-table-item'):
            title_div = item.find('div', class_='item-title')
            data_div = item.find('div', class_='item-data')
            if not title_div or not data_div:
                continue
            
            title = title_div.get_text(strip=True)
            input_field = data_div.find('input')
            value = input_field.get('value', '') if input_field else data_div.get_text(strip=True)
            
            info.raw_data[title] = value
            
            if title == '학번':
                info.student_id = value
            elif title == '한글성명':
                info.name_korean = value
            elif title == '영문성명(성)':
                info.name_english_first = value
            elif title == '영문성명(이름)':
                info.name_english_last = value
            elif title == '학년':
                info.grade = value.replace('학년', '').strip()
            elif title == '학적상태':
                info.status = value
            elif title == '학부(과)':
                info.department = value
            elif title == '상담교수':
                info.advisor = value
            elif title == '학생설계전공지도교수':
                info.design_advisor = value
            elif '전화번호' in title:
                info.phone = data_div.find('input', {'name': 'std_tel'}).get('value', '')
            elif title == '휴대폰':
                info.mobile = data_div.find('input', {'name': 'htel'}).get('value', '')
            elif title == 'E-Mail':
                info.email = data_div.find('input', {'name': 'email'}).get('value', '')
            elif '현거주지' in title:
                zip1 = data_div.find('input', {'name': 'zip1'})
                zip2 = data_div.find('input', {'name': 'zip2'})
                info.current_zip = f"{zip1.get('value', '')}-{zip2.get('value', '')}" if zip1 and zip2 else ''
                info.current_address1 = data_div.find('input', {'name': 'addr1'}).get('value', '')
                info.current_address2 = data_div.find('input', {'name': 'addr2'}).get('value', '')
            elif '주민등록' in title:
                zip1_2 = data_div.find('input', {'name': 'zip1_2'})
                zip2_2 = data_div.find('input', {'name': 'zip2_2'})
                info.registered_zip = f"{zip1_2.get('value', '')}-{zip2_2.get('value', '')}" if zip1_2 and zip2_2 else ''
                info.registered_address1 = data_div.find('input', {'name': 'addr1_2'}).get('value', '')
                info.registered_address2 = data_div.find('input', {'name': 'addr2_2'}).get('value', '')
            elif '명지포커스' in title:
                checkbox = data_div.find('input', {'name': 'focus_yn'})
                info.focus_newsletter = checkbox and checkbox.get('checked') is not None
        
        if not info.student_id:
            raise PageParsingError("학생 정보를 찾을 수 없습니다 (학번 필드 누락).")
        
        if self.verbose:
            log_success("학생 정보 파싱 완료")
        
        return info
