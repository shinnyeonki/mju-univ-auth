"""
인증 모듈
=========
Authenticator 클래스를 정의합니다.
"""

import time
from typing import Optional
from urllib.parse import urlparse, urljoin
import requests

import logging

from .results import MjuUnivAuthResult, ErrorCode
from .config import SERVICES, TIMEOUT_CONFIG, DEFAULT_HEADERS
from .infrastructure.parser import HTMLParser
from .infrastructure.crypto import generate_session_key, encrypt_with_rsa, encrypt_with_aes
from .exceptions import (
    MjuUnivAuthError,
    InvalidCredentialsError,
    NetworkError,
    ServiceNotFoundError,
    PageParsingError,
    SessionExpiredError,
)
from .utils import mask_sensitive

logger = logging.getLogger(__name__)


class Authenticator:
    """명지대학교 SSO 인증을 처리하는 클래스"""
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        verbose: bool = False,
    ):
        """
        Args:
            user_id: 학번/교번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부
        """
        self._user_id = user_id
        self._user_pw = user_pw
        self._verbose = verbose

        # 로그인 과정에서 획득한 데이터
        self._public_key: Optional[str] = None
        self._csrf_token: Optional[str] = None
        self._form_action: Optional[str] = None
        self._session: Optional[requests.Session] = None

    def login(self, service: str = 'msi') -> MjuUnivAuthResult[requests.Session]:
        """
        SSO 로그인 수행
        
        Args:
            service: 로그인할 서비스 (기본값: 'msi')
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 로그인 결과
        """
        session = requests.Session()
        try:
            self._execute_login(session, service)
            
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

    def _execute_login(self, session: requests.Session, service: str):
        """
        실제 SSO 로그인 로직

        Args:
            session: 사용할 requests.Session 객체
            service: 로그인할 서비스

        Raises:
            ServiceNotFoundError: 알 수 없는 서비스
            InvalidCredentialsError: 로그인 정보가 틀렸을 때
            PageParsingError: 로그인 페이지 파싱에 실패했을 때
            NetworkError: 네트워크 요청에 실패했을 때
        """
        if service not in SERVICES:
            raise ServiceNotFoundError(service, list(SERVICES.keys()))

        # 전달받은 세션 저장 및 기본 헤더 설정
        self._session = session
        self._session.headers.update(DEFAULT_HEADERS)
        
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
            raise PageParsingError("공개키(public-key)를 찾을 수 없습니다.", field="public-key")
        if not csrf_token:
            raise PageParsingError("CSRF 토큰(c_r_t)을 찾을 수 없습니다.", field="c_r_t")
        if not form_action:
            raise PageParsingError("로그인 폼(signin-form)을 찾을 수 없습니다.", field="signin-form")

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

    def _handle_redirects(self, response, final_url: str, max_redirects: int = 10):
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

                try:
                    response = self._session.get(redirect_url, timeout=TIMEOUT_CONFIG.login)
                except requests.RequestException as e:
                    raise NetworkError("리다이렉트 실패", url=redirect_url, original_error=e)
                    
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
