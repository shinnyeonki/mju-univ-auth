"""
표준 인증 모듈
===============
StandardAuthenticator 클래스를 정의합니다.
"""
import time
from typing import Optional
from urllib.parse import urlparse, urljoin
import requests
import logging

from .base_authenticator import BaseAuthenticator
from ..config import SERVICES, TIMEOUT_CONFIG, DEFAULT_HEADERS
from ..infrastructure.parser import HTMLParser
from ..infrastructure.crypto import generate_session_key, encrypt_with_rsa, encrypt_with_aes
from ..exceptions import (
    MjuUnivAuthError,
    InvalidCredentialsError,
    NetworkError,
    ServiceNotFoundError,
    ParsingError,
    AlreadyLoggedInError,
)
from ..utils import mask_sensitive

logger = logging.getLogger(__name__)


class StandardAuthenticator(BaseAuthenticator):
    """명지대학교 표준 SSO 인증을 처리하는 클래스"""

    def __init__(
        self,
        user_id: str,
        user_pw: str,
        verbose: bool = False,
    ):
        super().__init__(user_id, user_pw, verbose)
        # 로그인 과정에서 획득한 데이터
        self._public_key: Optional[str] = None
        self._csrf_token: Optional[str] = None
        self._form_action: Optional[str] = None

    def _execute_login(self, session: requests.Session, service: str):
        """
        실제 SSO 로그인 로직

        Args:
            session: 사용할 requests.Session 객체
            service: 로그인할 서비스

        Raises:
            ServiceNotFoundError: 알 수 없는 서비스
            InvalidCredentialsError: 로그인 정보가 틀렸을 때
            ParsingError: 로그인 페이지 파싱에 실패했을 때
            NetworkError: 네트워크 요청에 실패했을 때
            AlreadyLoggedInError: 이미 로그인된 세션일 때
        """
        # 전달받은 세션 저장 및 기본 헤더 설정
        self._session = session
        self._session.headers.update(DEFAULT_HEADERS)

        if self.is_session_valid(service):
            raise AlreadyLoggedInError(f"'{service}' 서비스에 이미 로그인되어 있습니다.")

        if service not in SERVICES:
            raise ServiceNotFoundError(service, list(SERVICES.keys()))

        service_config = SERVICES[service]

        if self._verbose:
            logger.info(f"===== MJU SSO 로그인: {service_config.name} =====")
            logger.info(f"User ID: {mask_sensitive(self._user_id)}")

        # Step 1: 로그인 페이지 접속 및 파싱
        self._fetch_login_page(service_config.auth_url)

        # Step 2: 암호화 데이터 준비
        encrypted_data = self._prepare_encrypted_data()

        # Step 3: 로그인 요청 전송
        response = self._submit_login(service_config.auth_url, encrypted_data)

        # Step 4: JS 리다이렉트/폼 처리 (최종 URL에 도달할 때까지)
        response = self._handle_redirects(response, service_config.final_url)

        # Step 5: 결과 확인
        self._validate_login_result(response, service_config)

        if self._verbose:
            logger.info(f"✓ 로그인 성공! ({service_config.name})")

    
    def _fetch_login_page(self, login_url: str) -> None:
        """로그인 페이지 접속 및 필요 정보 파싱"""
        if self._verbose:
            logger.info("[Step 1] 로그인 페이지 접속")
            logger.debug(f"GET {login_url}")

        try:
            response = self._session.get(login_url, timeout=TIMEOUT_CONFIG.default)
        except requests.RequestException as e:
            raise NetworkError("로그인 페이지 접속 실패", url=login_url, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")
            logger.info("[Step 1-2] 로그인 페이지 파싱")

        # 페이지 파싱
        public_key, csrf_token, form_action = HTMLParser.extract_login_page_data(response.text)

        if not public_key:
            raise ParsingError("공개키(public-key)를 찾을 수 없습니다.", field="public-key")
        if not csrf_token:
            raise ParsingError("CSRF 토큰(c_r_t)을 찾을 수 없습니다.", field="c_r_t")
        if not form_action:
            raise ParsingError("로그인 폼(signin-form)을 찾을 수 없습니다.", field="signin-form")

        self._public_key = public_key
        self._csrf_token = csrf_token
        self._form_action = form_action

        if self._verbose:
            logger.debug(f"Public Key: {public_key[:50]}..." if len(public_key) > 50 else f"Public Key: {public_key}")
            logger.debug(f"CSRF Token: {csrf_token}")
            logger.debug(f"Form Action: {form_action}")
            logger.info("✓ 페이지 파싱 완료")

    def _prepare_encrypted_data(self) -> dict:
        """암호화된 로그인 데이터 준비"""
        if self._verbose:
            logger.info("[Step 2] 암호화 데이터 준비")

        # 1. 세션키 생성
        key_info = generate_session_key(32)
        if self._verbose:
            logger.debug(f"Session Key: {key_info['keyStr'][:16]}...({len(key_info['keyStr'])} chars)")

        # 2. 타임스탬프 생성
        timestamp = str(int(time.time() * 1000))

        # 3. RSA 암호화 (keyStr + 타임스탬프)
        rsa_payload = f"{key_info['keyStr']},{timestamp}"
        encsymka = encrypt_with_rsa(rsa_payload, self._public_key)

        # 4. AES 암호화 (비밀번호)
        pw_enc = encrypt_with_aes(self._user_pw, key_info)

        if self._verbose:
            logger.info("✓ 암호화 완료")

        return {
            'user_id': self._user_id,
            'pw': '',
            'pw_enc': pw_enc,
            'encsymka': encsymka,
            'c_r_t': self._csrf_token,
            'user_id_enc': '',
        }

    def _submit_login(self, login_url: str, encrypted_data: dict):
        """로그인 요청 전송"""
        if self._verbose:
            logger.info("[Step 3] 로그인 요청 전송")

        # Form Action URL 구성
        if self._form_action.startswith('/'):
            action_url = f"https://sso.mju.ac.kr{self._form_action}"
        else:
            action_url = self._form_action

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://sso.mju.ac.kr',
            'Referer': login_url,
            'Upgrade-Insecure-Requests': '1',
        }

        if self._verbose:
            logger.debug(f"POST {action_url}")

        try:
            response = self._session.post(
                action_url,
                data=encrypted_data,
                headers=headers,
                timeout=TIMEOUT_CONFIG.login,
            )
        except requests.RequestException as e:
            raise NetworkError("로그인 요청 실패", url=action_url, original_error=e)
        
        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        return response

    def _is_final_url_reached(self, current_url: str, final_url: str) -> bool:
        """최종 URL에 도달했는지 확인"""
        current_parsed = urlparse(current_url)
        final_parsed = urlparse(final_url)
        
        return (current_parsed.netloc == final_parsed.netloc and 
                current_parsed.path.rstrip('/') == final_parsed.path.rstrip('/'))

    def _handle_redirects(self, response, final_url: str, max_redirects: int = 3):
        """JavaScript 폼 제출 및 리다이렉트 처리 (최종 URL에 도달할 때까지)"""
        for i in range(max_redirects):
            # 최종 URL에 도달했으면 중단
            if self._is_final_url_reached(response.url, final_url):
                if self._verbose:
                    logger.debug(f"Final URL: {response.url}")
                break
                
            # 1. JavaScript 폼 자동 제출 처리
            if HTMLParser.has_js_form_submit(response.text):
                action, form_data = HTMLParser.extract_form_data(response.text)
                if action and form_data:
                    if self._verbose:
                        logger.info(f"[Step 3-{i+2}] JS 폼 자동 제출 처리")

                    action_url = self._build_absolute_url(response.url, action)
                    if self._verbose:
                        logger.debug(f"Form Action: {action_url}")

                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': f"https://{urlparse(response.url).netloc}",
                        'Referer': response.url,
                    }

                    try:
                        response = self._session.post(
                            action_url,
                            data=form_data,
                            headers=headers,
                            timeout=TIMEOUT_CONFIG.login,
                        )
                    except requests.RequestException as e:
                        raise NetworkError("폼 제출 실패", url=action_url, original_error=e)
                    
                    if self._verbose:
                        logger.debug(f"Response: {response.status_code} - {response.url}")
                    continue

            # 2. location.href 리다이렉트 처리
            redirect_url = HTMLParser.extract_js_redirect(response.text)
            if redirect_url:
                if self._verbose:
                    logger.info(f"[Step 3-{i+2}] JS 리다이렉트 따라가기")
                    logger.debug(f"JS Redirect URL: {redirect_url}")

                # 응답 URL을 사용하여 상대 리다이렉트를 절대 URL로 변환
                action_url = self._build_absolute_url(response.url, redirect_url)
                if self._verbose:
                    logger.debug(f"Resolved JS Redirect URL: {action_url}")

                try:
                    response = self._session.get(action_url, timeout=TIMEOUT_CONFIG.login)
                except requests.RequestException as e:
                    raise NetworkError("리다이렉트 실패", url=action_url, original_error=e)
                    
                if self._verbose:
                    logger.debug(f"Response: {response.status_code} - {response.url}")
                continue

            # 더 이상 처리할 JS 동작이 없음
            break

        return response

    def _build_absolute_url(self, base_url: str, path: str) -> str:
        """상대 경로를 절대 URL로 변환"""
        if path.startswith('http'):
            return path
        return urljoin(base_url, path)

    def _validate_login_result(self, response, service_config) -> None:
        """로그인 결과 검증"""
        if self._verbose:
            logger.info("[Step 4] 로그인 결과 확인")

        html = response.text
        current_url = response.url

        # 최종 URL에 도달했는지 확인
        final_url_reached = self._is_final_url_reached(current_url, service_config.final_url)

        # 로그인 폼이 다시 나타났는지 확인
        has_signin_form = HTMLParser.has_signin_form(html)

        # 로그아웃 버튼이 있는지 확인
        has_logout = HTMLParser.has_logout_button(html)

        # 성공 판정: 최종 URL에 도착했고 로그인 폼이 없으면 성공
        if (final_url_reached and not has_signin_form) or (has_logout and not has_signin_form):
            return

        # 실패 판정: 로그인 폼이 다시 나타났으면 실패
        if has_signin_form:
            error_msg = HTMLParser.extract_error_message(html)
            if error_msg:
                if self._verbose:
                    logger.error("로그인 실패")
                    logger.error(f"Server Error: {error_msg}")
                raise InvalidCredentialsError(error_msg, service=service_config.name)

            if self._verbose:
                logger.error("로그인 실패")
                logger.error("원인: 로그인 폼이 다시 표시됨 (인증 실패)")
            raise InvalidCredentialsError("인증 실패 (로그인 정보를 확인해주세요)", service=service_config.name)

        # 알 수 없는 상태
        if self._verbose:
            logger.warning("로그인 결과 불확실")
        raise MjuUnivAuthError("알 수 없는 오류가 발생했습니다.")

    def is_session_valid(self, service: str = 'msi') -> bool:
        """
        현재 세션이 유효한지 가볍게 체크합니다.
        주로 메인 페이지에 접속하여 로그인 폼이 나타나는지 확인하는 방식으로 동작합니다.

        Args:
            service: 확인할 서비스 (기본값: 'msi')

        Returns:
            bool: 세션이 유효하면 True, 아니면 False
        """
        if self._session is None:
            if self._verbose:
                logger.warning("세션이 존재하지 않습니다. 먼저 로그인을 수행해야 합니다.")
            return False

        if service not in SERVICES:
            if self._verbose:
                logger.error(f"알 수 없는 서비스: {service}")
            return False

        service_config = SERVICES[service]
        check_url = service_config.final_url

        if self._verbose:
            logger.info(f"===== 세션 유효성 검사: {service_config.name} =====")
            logger.debug(f"GET {check_url}")

        try:
            response = self._session.get(check_url, timeout=TIMEOUT_CONFIG.default, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException as e:
            if self._verbose:
                logger.error(f"세션 유효성 검사 중 네트워크 오류 발생: {e}")
            return False

        if self._verbose:
            logger.debug(f"Response: {response.status_code} - {response.url}")

        html = response.text

        # 로그아웃 버튼이 있으면 세션 유효
        has_logout = HTMLParser.has_logout_button(html)
        if has_logout:
            if self._verbose:
                logger.info("✓ 세션이 유효합니다. (로그아웃 버튼 확인)")
            return True
        
        # 로그인 폼이 있으면 세션 무효
        has_signin_form = HTMLParser.has_signin_form(html)
        if has_signin_form:
            if self._verbose:
                logger.warning("세션이 만료되었거나 유효하지 않습니다. (로그인 폼 확인)")
            return False

        # 최종 URL에 도달했고 로그인 폼이 없는 경우도 세션 유효
        final_url_reached = self._is_final_url_reached(response.url, service_config.final_url)
        if final_url_reached:
            if self._verbose:
                logger.info("✓ 세션이 유효합니다. (최종 URL 도달 및 로그인 폼 없음)")
            return True

        if self._verbose:
            logger.warning("세션 유효성을 확인할 수 없습니다. (알 수 없는 상태)")
        return False

