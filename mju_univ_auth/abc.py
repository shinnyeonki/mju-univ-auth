"""
myiweb 모듈의 추상 기본 클래스
=============================
"""

import re
from abc import ABC, abstractmethod
from typing import Optional

import requests

from .exceptions import NetworkError, PageParsingError, SessionExpiredError
from .utils import log_step, log_request, log_response, log_info, log_success


class BaseFetcher(ABC):
    """
    모든 Fetcher의 기반이 되는 추상 클래스
    """
    MSI_HOME_URL = "https://msi.mju.ac.kr/servlet/security/MySecurityStart"

    def __init__(self, session: requests.Session, user_pw: str, verbose: bool = True):
        """
        Args:
            session: 로그인된 requests 세션
            user_pw: 비밀번호 (2차 인증 등에 사용될 수 있음)
            verbose: 상세 로그 출력 여부
        """
        self.session = session
        self.user_pw = user_pw
        self.verbose = verbose
        self.csrf_token: Optional[str] = None
        self._last_url: Optional[str] = None

    @abstractmethod
    def fetch(self):
        """
        데이터를 조회하여 해당 데이터 클래스 객체를 반환합니다.
        이 메서드는 하위 클래스에서 반드시 구현되어야 합니다.
        """
        raise NotImplementedError

    def _get_csrf_token(self):
        """MSI 홈페이지에서 CSRF 토큰을 추출하여 self.csrf_token에 저장합니다."""
        if self.verbose:
            log_step("A-1", "CSRF 토큰 추출")
            log_request('GET', self.MSI_HOME_URL)

        try:
            response = self.session.get(self.MSI_HOME_URL, timeout=10)

            if self.verbose:
                log_response(response, show_body=False)

            if 'sso.mju.ac.kr' in response.url:
                raise SessionExpiredError("세션이 만료되었습니다. 다시 로그인해주세요.")

            self.csrf_token = self._extract_csrf_from_html(response.text)

            if not self.csrf_token:
                raise PageParsingError("CSRF 토큰을 찾을 수 없습니다.")

            if self.verbose:
                log_info("CSRF Token", self.csrf_token)
                log_success("CSRF 토큰 추출 완료")

        except requests.RequestException as e:
            raise NetworkError(f"CSRF 토큰 추출 실패: {e}") from e

    def _extract_csrf_from_html(self, html: str) -> Optional[str]:
        """HTML에서 CSRF 토큰을 추출합니다."""
        # meta 태그에서 추출
        csrf_match = re.search(r'meta[^>]*_csrf[^>]*content="([^"]+)"', html)
        if csrf_match:
            return csrf_match.group(1)

        # X-CSRF-TOKEN 헤더 설정에서 추출 (JavaScript 내)
        csrf_match = re.search(r"X-CSRF-TOKEN[\"']?\s*:\s*[\"']([^\"']+)[\"']", html)
        if csrf_match:
            return csrf_match.group(1)

        # input hidden 태그에서 추출
        csrf_match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        if csrf_match:
            return csrf_match.group(1)

        return None
