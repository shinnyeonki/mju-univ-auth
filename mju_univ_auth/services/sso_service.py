"""
SSO 로그인 서비스
================
명지대학교 SSO 로그인을 처리하는 서비스 클래스입니다.
"""

import time
from typing import Optional
from urllib.parse import urlparse

from ..config.settings import SERVICES, TIMEOUT_CONFIG
from ..infrastructure.http_client import HTTPClient
from ..infrastructure.parser import HTMLParser
from ..infrastructure.crypto import generate_session_key, encrypt_with_rsa, encrypt_with_aes
from ..exceptions import (
    MjuUnivAuthError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError,
    ServiceNotFoundError,
)
from ..utils import Logger, get_logger, mask_sensitive


class SSOService:
    """명지대학교 SSO 로그인 서비스"""
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        http_client: Optional[HTTPClient] = None,
        logger: Optional[Logger] = None,
    ):
        """
        Args:
            user_id: 학번/교번
            user_pw: 비밀번호
            http_client: HTTP 클라이언트 (주입 또는 새로 생성)
            logger: 로거 (주입 또는 NullLogger)
        """
        self.user_id = user_id
        self.user_pw = user_pw
        self.http = http_client or HTTPClient()
        self.logger = logger or get_logger(False)
        
        # 로그인 과정에서 획득한 데이터
        self._public_key: Optional[str] = None
        self._csrf_token: Optional[str] = None
        self._form_action: Optional[str] = None
    
    def login(self, service: str = 'msi') -> HTTPClient:
        """
        SSO 로그인 수행
        
        Args:
            service: 로그인할 서비스 ('lms', 'portal', 'library', 'msi', 'myicap')
        
        Returns:
            HTTPClient: 로그인된 HTTP 클라이언트
        
        Raises:
            ServiceNotFoundError: 알 수 없는 서비스
            InvalidCredentialsError: 로그인 정보가 틀렸을 때
            PageParsingError: 로그인 페이지 파싱에 실패했을 때
            NetworkError: 네트워크 요청에 실패했을 때
        """
        if service not in SERVICES:
            raise ServiceNotFoundError(service, list(SERVICES.keys()))
        
        service_config = SERVICES[service]
        
        self.logger.section(f"MJU SSO 로그인: {service_config.name}")
        self.logger.info("User ID", mask_sensitive(self.user_id))
        
        # Step 1: 로그인 페이지 접속 및 파싱
        self._fetch_login_page(service_config.auth_url)
        
        # Step 2: 암호화 데이터 준비
        encrypted_data = self._prepare_encrypted_data()
        
        # Step 3: 로그인 요청 전송
        response = self._submit_login(service_config.auth_url, encrypted_data)
        
        # Step 4: JS 리다이렉트/폼 처리
        response = self._handle_redirects(response)
        
        # Step 5: 결과 확인
        self._validate_login_result(response, service_config)
        
        self.logger.success(f"로그인 성공! ({service_config.name})")
        return self.http
    
    def _fetch_login_page(self, login_url: str) -> None:
        """로그인 페이지 접속 및 필요 정보 파싱"""
        self.logger.step("1", "로그인 페이지 접속")
        self.logger.request('GET', login_url)
        
        response = self.http.get(login_url, timeout=TIMEOUT_CONFIG.default)
        self.logger.response(response)
        
        # 페이지 파싱
        self.logger.step("1-2", "로그인 페이지 파싱")
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
        
        self.logger.info("Public Key", public_key[:50] + "..." if len(public_key) > 50 else public_key)
        self.logger.info("CSRF Token", csrf_token)
        self.logger.info("Form Action", form_action)
        self.logger.success("페이지 파싱 완료")
    
    def _prepare_encrypted_data(self) -> dict:
        """암호화된 로그인 데이터 준비"""
        self.logger.step("2", "암호화 데이터 준비")
        
        # 1. 세션키 생성
        key_info = generate_session_key(32)
        self.logger.info("Session Key", f"{key_info['keyStr'][:16]}...({len(key_info['keyStr'])} chars)", 4)
        
        # 2. 타임스탬프 생성
        timestamp = str(int(time.time() * 1000))
        
        # 3. RSA 암호화 (keyStr + 타임스탬프)
        rsa_payload = f"{key_info['keyStr']},{timestamp}"
        encsymka = encrypt_with_rsa(rsa_payload, self._public_key)
        
        # 4. AES 암호화 (비밀번호)
        pw_enc = encrypt_with_aes(self.user_pw, key_info)
        
        self.logger.success("암호화 완료")
        
        return {
            'user_id': self.user_id,
            'pw': '',
            'pw_enc': pw_enc,
            'encsymka': encsymka,
            'c_r_t': self._csrf_token,
            'user_id_enc': '',
        }
    
    def _submit_login(self, login_url: str, encrypted_data: dict):
        """로그인 요청 전송"""
        self.logger.step("3", "로그인 요청 전송")
        
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
        
        self.logger.request('POST', action_url, headers, encrypted_data)
        
        response = self.http.post(
            action_url,
            data=encrypted_data,
            headers=headers,
            timeout=TIMEOUT_CONFIG.login,
        )
        self.logger.response(response)
        
        return response
    
    def _handle_redirects(self, response, max_redirects: int = 2):
        """JavaScript 폼 제출 및 리다이렉트 처리"""
        for i in range(max_redirects):
            # 1. JavaScript 폼 자동 제출 처리
            if HTMLParser.has_js_form_submit(response.text):
                action, form_data = HTMLParser.extract_form_data(response.text)
                if action and form_data:
                    self.logger.step(f"3-{i+2}", "JS 폼 자동 제출 처리")
                    
                    action_url = self.http.build_absolute_url(response.url, action)
                    self.logger.info("Form Action", action_url, 4)
                    
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Origin': f"https://{self.http.get_domain(response.url)}",
                        'Referer': response.url,
                    }
                    
                    response = self.http.post(
                        action_url,
                        data=form_data,
                        headers=headers,
                        timeout=TIMEOUT_CONFIG.login,
                    )
                    self.logger.response(response)
                    continue
            
            # 2. location.href 리다이렉트 처리
            redirect_url = HTMLParser.extract_js_redirect(response.text)
            if redirect_url:
                self.logger.step(f"3-{i+2}", "JS 리다이렉트 따라가기")
                self.logger.info("JS Redirect URL", redirect_url, 4)
                
                response = self.http.get(redirect_url, timeout=TIMEOUT_CONFIG.login)
                self.logger.response(response)
                continue
            
            # 더 이상 처리할 JS 동작이 없음
            break
        
        return response
    
    def _validate_login_result(self, response, service_config) -> None:
        """로그인 결과 검증"""
        self.logger.step("4", "로그인 결과 확인")
        
        html = response.text
        final_url = response.url
        
        # 대상 도메인으로 이동 확인
        parsed_url = urlparse(final_url)
        actually_redirected = service_config.success_domain in parsed_url.netloc
        
        # 로그인 폼이 다시 나타났는지 확인
        has_signin_form = HTMLParser.has_signin_form(html)
        
        # 로그아웃 버튼이 있는지 확인
        has_logout = HTMLParser.has_logout_button(html)
        
        # 성공 판정: 대상 도메인에 도착했고 로그인 폼이 없으면 성공
        if (actually_redirected and not has_signin_form) or (has_logout and not has_signin_form):
            return
        
        # 실패 판정: 로그인 폼이 다시 나타났으면 실패
        if has_signin_form:
            # 에러 메시지 확인
            error_msg = HTMLParser.extract_error_message(html)
            if error_msg:
                self.logger.error("로그인 실패")
                self.logger.info("Server Error", error_msg, 4)
                raise InvalidCredentialsError(error_msg, service=service_config.name)
            
            self.logger.error("로그인 실패")
            self.logger.info("원인", "로그인 폼이 다시 표시됨 (인증 실패)", 4)
            raise InvalidCredentialsError("인증 실패 (로그인 정보를 확인해주세요)", service=service_config.name)
        
        # 알 수 없는 상태
        self.logger.warning("로그인 결과 불확실")
        raise MjuUnivAuthError("알 수 없는 오류가 발생했습니다.")
    
    def test_session(self, service: str = 'msi') -> bool:
        """세션 유효성 테스트"""
        if service not in SERVICES:
            return False
        
        service_config = SERVICES[service]
        test_url = service_config.test_url
        
        self.logger.step("5", "세션 유효성 테스트")
        self.logger.info("Test URL", test_url)
        
        try:
            response = self.http.get(test_url, timeout=TIMEOUT_CONFIG.default)
            
            self.logger.info("응답 상태", response.status_code)
            self.logger.info("최종 URL", response.url)
            
            # SSO 또는 login_security로 리다이렉트되면 세션 만료
            if 'sso.mju.ac.kr' in response.url or 'login_security' in response.url:
                self.logger.warning("세션이 유효하지 않음 (로그인 페이지로 리다이렉트)")
                return False
            
            # 로그아웃 버튼이 있으면 유효한 세션
            if HTMLParser.has_logout_button(response.text):
                self.logger.success("세션 유효함")
                return True
            
            self.logger.warning("세션 상태 불확실")
            return False
            
        except NetworkError:
            self.logger.error("세션 테스트 실패")
            return False
