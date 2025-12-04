"""
수강신청 시스템 인증기
======================
명지대학교 수강신청 시스템(class.mju.ac.kr)의 인증을 처리하는 클래스입니다.
"""

from typing import Optional, Tuple
import requests
import logging

from .base_authenticator import BaseAuthenticator
from .results import MjuUnivAuthResult, ErrorCode
from .config import SERVICES, TIMEOUT_CONFIG, DEFAULT_HEADERS
from .exceptions import (
    InvalidCredentialsError,
    NetworkError,
    PageParsingError,
    ServiceNotFoundError,
)

logger = logging.getLogger(__name__)


class SugangAuthenticator(BaseAuthenticator):
    """
    명지대학교 수강신청 시스템 인증을 처리하는 클래스
    
    일반 SSO와 다른 별도의 인증 체계를 사용합니다.
    - 로그인 URL: https://class.mju.ac.kr/loginproc
    - CSRF 토큰 기반 인증
    """
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        service: str = 'sugang',
        verbose: bool = False,
    ):
        """
        Args:
            user_id: 학번
            user_pw: 비밀번호
            service: 서비스 이름 (기본값: 'sugang')
            verbose: 상세 로그 출력 여부
        """
        super().__init__(user_id, user_pw, verbose)
        self._service = service
        
        # 수강신청 시스템용 CSRF 토큰
        self._csrf_token: Optional[str] = None
        self._csrf_header: Optional[str] = None

    def authenticate(self) -> MjuUnivAuthResult[requests.Session]:
        """
        수강신청 시스템 로그인 수행
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 로그인 결과
        """
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        
        try:
            self._execute_login(session)
            
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=True,
                data=session
            )

        except InvalidCredentialsError as e:
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=False,
                error_code=ErrorCode.AUTH_FAILED,
                error_message=str(e)
            )
        except NetworkError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.NETWORK_ERROR,
                error_message=str(e)
            )
        except PageParsingError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.PARSE_ERROR,
                error_message=str(e)
            )
        except ServiceNotFoundError as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.SERVICE_NOT_FOUND,
                error_message=str(e)
            )
        except Exception as e:
            return MjuUnivAuthResult(
                request_succeeded=False,
                credentials_valid=False,
                error_code=ErrorCode.UNKNOWN,
                error_message=str(e)
            )

    def _execute_login(self, session: requests.Session) -> None:
        """
        실제 로그인 로직 수행
        
        Args:
            session: 사용할 requests.Session 객체
            
        Raises:
            ServiceNotFoundError: 서비스를 찾을 수 없는 경우
            NetworkError: 네트워크 요청 실패
            PageParsingError: CSRF 토큰 파싱 실패
            InvalidCredentialsError: 로그인 실패
        """
        if self._service not in SERVICES:
            raise ServiceNotFoundError(self._service, list(SERVICES.keys()))
        
        self._session = session
        service_config = SERVICES[self._service]
        endpoints = service_config.endpoints
        
        if self._verbose:
            logger.info(f"===== MJU 로그인: {service_config.name} =====")

        # Step 1: 로그인 페이지에서 CSRF 토큰 획득
        self._fetch_login_csrf_token(endpoints.LOGIN_PAGE)

        # Step 2: 로그인 요청
        response = self._submit_login(endpoints.LOGIN_PROC)

        # Step 3: 로그인 결과 검증
        self._validate_login_result(response, service_config)

        # Step 4: 메인 페이지 CSRF 토큰 캐싱 (AJAX 요청용)
        self._cache_main_csrf_token(endpoints.MAIN)

        if self._verbose:
            logger.info(f"✓ 로그인 성공! ({service_config.name})")

    def _fetch_login_csrf_token(self, login_url: str) -> None:
        """로그인 페이지에서 CSRF 토큰 추출"""
        if self._verbose:
            logger.info("[Step 1] 로그인 페이지 접속")
            logger.debug(f"GET {login_url}")

        try:
            response = self._session.get(login_url, timeout=TIMEOUT_CONFIG.default)
            response.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError("로그인 페이지 접속 실패", url=login_url, original_error=e)

        if self._verbose:
            logger.debug(f"Response: {response.status_code}")

        # BeautifulSoup으로 CSRF 토큰 파싱
        csrf_token = self._extract_csrf_from_html(response.text)
        
        if not csrf_token:
            raise PageParsingError("CSRF 토큰(_csrf)을 찾을 수 없습니다.", field="_csrf")

        self._csrf_token = csrf_token

        if self._verbose:
            logger.debug(f"CSRF Token: {csrf_token}")
            logger.info("✓ CSRF 토큰 획득 완료")

    def _extract_csrf_from_html(self, html: str) -> Optional[str]:
        """HTML에서 CSRF 토큰 추출"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input['value']
        except ImportError:
            # BeautifulSoup이 없으면 정규식으로 시도
            import re
            match = re.search(r'<input[^>]*name=["\']_csrf["\'][^>]*value=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1)
            # value가 먼저 올 수도 있음
            match = re.search(r'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']_csrf["\']', html)
            if match:
                return match.group(1)
        return None

    def _submit_login(self, login_proc_url: str) -> requests.Response:
        """로그인 요청 전송"""
        if self._verbose:
            logger.info("[Step 2] 로그인 요청 전송")

        login_data = {
            "username": self._user_id.strip(),
            "password": self._user_pw,
            "lang": "ko",
            "_csrf": self._csrf_token,
        }

        try:
            response = self._session.post(
                login_proc_url,
                data=login_data,
                allow_redirects=True,
                timeout=TIMEOUT_CONFIG.login,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise NetworkError("로그인 요청 실패", url=login_proc_url, original_error=e)

        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        return response

    def _validate_login_result(self, response: requests.Response, service_config) -> None:
        """로그인 결과 검증"""
        if self._verbose:
            logger.info("[Step 3] 로그인 결과 확인")

        final_url = response.url
        content = response.text

        # 성공: 메인 페이지로 리다이렉트
        if "main" in final_url:
            if self._verbose:
                logger.debug(f"Final URL: {final_url}")
            return

        # 실패: 로그인 페이지로 돌아옴
        if "로그인" in content or "Sign in" in content or "login" in content.lower():
            raise InvalidCredentialsError(
                "인증 실패 (학번 또는 비밀번호를 확인해주세요)",
                service=service_config.name
            )

        # 알 수 없는 상태
        raise InvalidCredentialsError(
            "로그인 실패 (보안 차단 또는 일시적 오류)",
            service=service_config.name
        )

    def _cache_main_csrf_token(self, main_url: str) -> None:
        """메인 페이지에서 AJAX용 CSRF 토큰 캐싱"""
        if self._verbose:
            logger.info("[Step 4] AJAX용 CSRF 토큰 캐싱")

        try:
            response = self._session.get(f"{main_url}?lang=ko", timeout=TIMEOUT_CONFIG.default)
            response.raise_for_status()
        except requests.RequestException as e:
            if self._verbose:
                logger.warning(f"메인 페이지 접속 실패: {e}")
            return

        # 메타태그에서 CSRF 정보 추출
        csrf_token, csrf_header = self._extract_meta_csrf(response.text)
        
        if csrf_token and csrf_header:
            self._csrf_token = csrf_token
            self._csrf_header = csrf_header
            if self._verbose:
                logger.debug(f"CSRF Header: {csrf_header}")
                logger.debug(f"CSRF Token: {csrf_token}")
                logger.info("✓ AJAX용 CSRF 토큰 캐싱 완료")
        else:
            if self._verbose:
                logger.warning("CSRF 메타태그를 찾을 수 없습니다.")

    def _extract_meta_csrf(self, html: str) -> Tuple[Optional[str], Optional[str]]:
        """메타태그에서 CSRF 토큰과 헤더명 추출"""
        csrf_token = None
        csrf_header = None
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            csrf_meta = soup.find('meta', {'name': '_csrf'})
            csrf_header_meta = soup.find('meta', {'name': '_csrf_header'})
            
            if csrf_meta and csrf_meta.get('content'):
                csrf_token = csrf_meta['content']
            if csrf_header_meta and csrf_header_meta.get('content'):
                csrf_header = csrf_header_meta['content']
                
        except ImportError:
            # BeautifulSoup이 없으면 정규식으로 시도
            import re
            token_match = re.search(r'<meta[^>]*name=["\']_csrf["\'][^>]*content=["\']([^"\']+)["\']', html)
            header_match = re.search(r'<meta[^>]*name=["\']_csrf_header["\'][^>]*content=["\']([^"\']+)["\']', html)
            
            if token_match:
                csrf_token = token_match.group(1)
            if header_match:
                csrf_header = header_match.group(1)
                
        return csrf_token, csrf_header

    def get_csrf_info(self) -> Tuple[str, str]:
        """
        캐시된 CSRF 토큰과 헤더명 반환 (AJAX 요청용)
        
        Returns:
            Tuple[str, str]: (헤더명, 토큰값)
            
        Raises:
            ValueError: CSRF 정보가 없는 경우
        """
        if not self._csrf_token or not self._csrf_header:
            raise ValueError("CSRF 정보가 캐시되지 않았습니다. 로그인을 먼저 수행하세요.")
        return self._csrf_header, self._csrf_token
