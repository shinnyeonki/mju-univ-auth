"""
학적변동내역 조회 모듈
=======================
MSI 서비스에서 학적변동내역을 조회하고 파싱합니다.
학생카드 조회와 달리, 2차 비밀번호 인증이 필요하지 않습니다.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any

import requests
from bs4 import BeautifulSoup, SoupStrainer

from .abc import BaseFetcher
from .utils import Colors, log_info, log_section, log_step, log_request, log_response, log_success
from .exceptions import NetworkError, PageParsingError


@dataclass
class StudentChangeLog:
    """학적변동내역 정보 데이터 클래스"""
    student_id: str = ""       # 학번
    name: str = ""             # 성명
    status: str = ""           # 학적상태
    grade: str = ""            # 학년
    completed_semesters: str = "" # 이수학기
    department: str = ""       # 학부(과)

    @classmethod
    def fetch(cls, user_id: str, user_pw: str, verbose: bool = False) -> StudentChangeLog:
        """
        SSO 로그인부터 학적변동내역 조회까지 모든 과정을 수행합니다.

        Args:
            user_id: 학번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부

        Returns:
            조회된 학적변동내역 정보 객체
        """
        # 순환 참조 방지를 위해 메서드 내에서 임포트
        from .sso import MJUSSOLogin

        if verbose:
            log_section("myiweb 통합 실행: 학적변동내역")

        sso = MJUSSOLogin(user_id, user_pw, verbose=verbose)
        session = sso.login(service='msi')

        fetcher = _StudentChangeLogFetcher(session, user_pw, verbose=verbose)
        return fetcher.fetch()

    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 명시적인 딕셔너리로 변환합니다."""
        return {
            'student_id': self.student_id,
            'name': self.name,
            'status': self.status,
            'grade': self.grade,
            'completed_semesters': self.completed_semesters,
            'department': self.department,
        }

    def print_summary(self) -> None:
        """학적변동내역 정보 요약 출력"""
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f" 학적변동내역 조회 결과")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}")
        
        log_info("학번", self.student_id)
        log_info("성명", self.name)
        log_info("학적상태", self.status)
        log_info("학년", self.grade)
        log_info("이수학기", self.completed_semesters)
        log_info("학부(과)", self.department)


class _StudentChangeLogFetcher(BaseFetcher):
    """학적변동내역 조회 서비스 (내부용)"""

    CHANGE_LOG_URL = "/servlet/su/sud/Sud00Svl03viewChangeLog"

    def fetch(self) -> StudentChangeLog:
        """
        학적변동내역을 조회합니다.

        Returns:
            StudentChangeLog: 파싱된 학적변동내역 정보
        """
        if self.verbose:
            log_step("B", "학적변동내역 정보 조회 시작")

        # 1. CSRF 토큰 획득 (공통 로직)
        self._get_csrf_token()

        # 2. 학적변동내역 페이지 접근
        html = self._access_change_log_page()

        # 3. HTML 파싱
        info = self._parse_info(html)
        
        if self.verbose:
            log_success("학적변동내역 정보 조회 완료")
            info.print_summary()

        return info

    def _access_change_log_page(self) -> str:
        """학적변동내역 페이지에 접근하여 HTML을 반환합니다."""
        if self.verbose:
            log_step("B-2", "학적변동내역 페이지 접근")

        full_url = f"https://msi.mju.ac.kr{self.CHANGE_LOG_URL}"

        form_data = {
            'sysdiv': 'SCH',
            'subsysdiv': 'SCH',
            'folderdiv': '101',
            'pgmid': 'W_SUD020',  # 학적변동내역 프로그램 ID
            '_csrf': self.csrf_token,
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://msi.mju.ac.kr',
            'Referer': self.MSI_HOME_URL,
            'X-CSRF-TOKEN': self.csrf_token,
        }

        if self.verbose:
            log_request('POST', full_url, headers, form_data)

        try:
            response = self.session.post(full_url, data=form_data, headers=headers, timeout=15)
            if self.verbose:
                log_response(response, show_body=False)
            self._last_url = response.url
            return response.text
        except requests.RequestException as e:
            raise NetworkError(f"학적변동내역 페이지 접근 실패: {e}") from e

    def _parse_info(self, html: str) -> StudentChangeLog:
        """학적변동내역 HTML을 파싱합니다."""
        if self.verbose:
            log_step("B-3", "학적변동내역 정보 파싱")

        parse_only = SoupStrainer('div', class_='flex-table-item')
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        
        info = StudentChangeLog()

        for item in soup.find_all('div', class_='flex-table-item'):
            title_div = item.find('div', class_='item-title')
            data_div = item.find('div', class_='item-data')
            
            if not title_div or not data_div:
                continue
            
            title = title_div.get_text(strip=True)
            value = data_div.get_text(strip=True)
            
            if title == "학번":
                info.student_id = value
            elif title == "성명":
                info.name = value
            elif title == "학적상태":
                info.status = value
            elif title == "학년":
                info.grade = value
            elif title == "이수학기":
                info.completed_semesters = value
            elif title == "학부(과)":
                info.department = value

        if not info.student_id:
            raise PageParsingError("학적변동내역 정보를 찾을 수 없습니다 (학번 필드 누락).")

        if self.verbose:
            log_success("학적변동내역 정보 파싱 완료")

        return info
