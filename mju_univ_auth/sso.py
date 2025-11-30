import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup, SoupStrainer

from .utils import (
    Colors, log_section, log_step, log_info, log_success, log_error, 
    log_warning, log_request, log_response, mask_sensitive
)
from .crypto import generate_session_key, encrypt_with_rsa, encrypt_with_aes
from .exceptions import (
    MjuUnivAuthError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError
)


class MJUSSOLogin:
    """명지대학교 SSO 로그인 클래스"""
    
    # 서비스별 로그인 URL 설정
    SERVICES = {
        'lms': {
            'name': 'LMS (e-Class)',
            'url': 'https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=lms&state=Random%20String&redirect_uri=https://lms.mju.ac.kr/ilos/sso/sso_response.jsp',
            'success_domain': 'lms.mju.ac.kr',
            'test_url': 'https://lms.mju.ac.kr/ilos/main/main_form.acl'
        },
        'portal': {
            'name': 'Portal (통합정보시스템)',
            'url': 'https://sso.mju.ac.kr/sso/auth?client_id=portal&response_type=code&state=1764321341781&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fportal.mju.ac.kr%2Fsso%2Fresponse.jsp',
            'success_domain': 'portal.mju.ac.kr',
            'test_url': 'https://portal.mju.ac.kr/portal/main.do'
        },
        'library': {
            'name': 'Library (도서관)',
            'url': 'https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=library&state=state&redirect_uri=https://lib.mju.ac.kr/sso/login',
            'success_domain': 'lib.mju.ac.kr',
            'test_url': 'https://lib.mju.ac.kr/main'
        },
        'msi': {
            'name': 'MSI (My iWeb)',
            'url': 'https://sso.mju.ac.kr/sso/auth?client_id=msi&response_type=code&state=1764322070097&tkn_type=normal&redirect_uri=https%3A%2F%2Fmsi.mju.ac.kr%2Findex_Myiweb.jsp',
            'success_domain': 'msi.mju.ac.kr',
            'test_url': 'https://msi.mju.ac.kr/index_Myiweb.jsp'
        },
        'myicap': {
            'name': 'MyiCAP (비교과)',
            'url': 'https://sso.mju.ac.kr/sso/auth?client_id=myicap&response_type=code&state=1764322418883&rd_c_p=loginparam&tkn_type=normal&redirect_uri=https%3A%2F%2Fmyicap.mju.ac.kr%2Findex.jsp',
            'success_domain': 'myicap.mju.ac.kr',
            'test_url': 'https://myicap.mju.ac.kr/index.jsp'
        }
    }
    
    def __init__(self, user_id: str, user_pw: str, verbose: bool = True):
        """
        Args:
            user_id: 학번/교번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부
        """
        self.user_id = user_id
        self.user_pw = user_pw
        self.verbose = verbose
        
        # requests 세션 생성 (쿠키 자동 관리)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        # 로그인 과정에서 획득한 데이터
        self.public_key: Optional[str] = None
        self.csrf_token: Optional[str] = None
        self.form_action: Optional[str] = None
        
    def _parse_login_page(self, html: str):
        """로그인 페이지에서 필요한 정보 추출"""
        if self.verbose:
            log_step("1-2", "로그인 페이지 파싱")
        
        # 정규표현식 추출
        public_key_match = re.search(r'value=["\"]([^"\"]+)["\"][^>]*id=["\"]public-key["\"]', html)
        csrf_match = re.search(r'value=["\"]([^"\"]+)["\"][^>]*id=["\"]c_r_t["\"]', html)
        form_action_match = re.search(r'<form[^>]*id=["\"]signin-form["\"][^>]*action=["\"]([^"\"]+)["\"]', html)
        
        # 정규표현식으로 모두 찾은 경우 BeautifulSoup 스킵
        if public_key_match and csrf_match and form_action_match:
            self.public_key = public_key_match.group(1)
            self.csrf_token = csrf_match.group(1)
            self.form_action = form_action_match.group(1)
            
            if self.verbose:
                log_info("Public Key", self.public_key)
                log_info("CSRF Token", self.csrf_token)
                log_info("Form Action", self.form_action)
                log_success("페이지 파싱 완료 (regex)")
            return

        # 정규표현식 실패 시 lxml + SoupStrainer로 폴백
        parse_only = SoupStrainer(['input', 'form'])
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        
        # 1. 공개키 추출
        public_key_input = soup.find('input', {'id': 'public-key'})
        if not public_key_input:
            raise PageParsingError("공개키(public-key)를 찾을 수 없습니다.")
        self.public_key = public_key_input.get('value')
        
        if self.verbose:
            log_info("Public Key", self.public_key)
        
        # 2. CSRF 토큰 추출
        csrf_input = soup.find('input', {'id': 'c_r_t'})
        if not csrf_input:
            raise PageParsingError("CSRF 토큰(c_r_t)을 찾을 수 없습니다.")
        self.csrf_token = csrf_input.get('value')
        
        if self.verbose:
            log_info("CSRF Token", self.csrf_token)
        
        # 3. Form Action URL 추출
        form = soup.find('form', {'id': 'signin-form'})
        if not form:
            raise PageParsingError("로그인 폼(signin-form)을 찾을 수 없습니다.")
        self.form_action = form.get('action')
        
        if self.verbose:
            log_info("Form Action", self.form_action)
            log_success("페이지 파싱 완료")

    def _handle_js_form_submit(self, response: requests.Response, step: int) -> Optional[requests.Response]:
        """
        JavaScript 자동 폼 제출 처리
        
        예: <body onLoad="doLogin()">
            <form action="/servlet/login_security" method="post">
                <input name="code" value="..."/>
                <input name="_csrf" value="..."/>
            </form>
        
        Args:
            response: 현재 응답
            step: 현재 단계 번호 (로깅용)
        
        Returns:
            폼 제출 후 응답, 또는 None (폼이 없는 경우)
        """
        html = response.text
        
        # onLoad에서 폼 제출하는 패턴 감지
        if 'onLoad=' not in html or ('submit()' not in html and 'doLogin()' not in html):
            return None
        
        # 정규표현식으로 빠르게 폼 데이터 추출 시도
        form_action_match = re.search(r'<form[^>]*action=["\"]([^"\"]+)["\"]', html)
        if not form_action_match:
            return None
        
        action = form_action_match.group(1)
        if not action:
            return None
        
        # hidden input들 추출
        input_pattern = re.compile(r'<input[^>]*name=["\"]([^"\"]+)["\"][^>]*value=["\"]([^"\"]*)["\"]|<input[^>]*value=["\"]([^"\"]*)["\"][^>]*name=["\"]([^"\"]+)["\"]')
        form_data = {}
        for match in input_pattern.finditer(html):
            if match.group(1):
                form_data[match.group(1)] = match.group(2)
            elif match.group(4):
                form_data[match.group(4)] = match.group(3)
        
        if not form_data:
            # 정규표현식 실패 시 lxml로 폴백
            parse_only = SoupStrainer('form')
            soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
            form = soup.find('form')
            if not form:
                return None
            for input_tag in form.find_all('input'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    form_data[name] = value
        
        if not form_data:
            return None
        
        # 절대 URL로 변환
        from urllib.parse import urljoin
        action_url = urljoin(response.url, action)
        
        if self.verbose:
            log_step(f"3-{step+2}", f"JS 폼 자동 제출 처리")
            log_info("Form Action", action_url, 4)
            # 민감 정보 마스킹
            safe_data = {k: (mask_sensitive(v) if k in ('user_id', 'password', 'pw') else v[:30]+'...' if len(str(v)) > 30 else v) for k, v in form_data.items()}
            log_info("Form Data", str(safe_data), 4)
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': f"https://{response.url.split('/')[2]}",
            'Referer': response.url,
        }
        
        return self.session.post(action_url, data=form_data, headers=headers, allow_redirects=True, timeout=15)

    def _prepare_encrypted_data(self) -> dict:
        """암호화된 로그인 데이터 준비"""
        if self.verbose:
            log_step("2", "암호화 데이터 준비")
        
        # 1. 세션키 생성 (PBKDF2 파생 키 포함)
        key_info = generate_session_key(32)
        
        if self.verbose:
            log_info("Session Key (keyStr)", f"{key_info['keyStr'][:16]}...({len(key_info['keyStr'])} chars)", 4)
        
        # 2. 타임스탬프 생성
        timestamp = str(int(time.time() * 1000))
        
        # 3. RSA 암호화 (keyStr + 타임스탬프) - 서버로 keyStr 전송
        rsa_payload = f"{key_info['keyStr']},{timestamp}"
        encsymka = encrypt_with_rsa(rsa_payload, self.public_key, verbose=self.verbose)
        
        # 4. AES 암호화 (비밀번호) - PBKDF2로 파생된 key와 iv 사용
        pw_enc = encrypt_with_aes(self.user_pw, key_info, verbose=self.verbose)
        
        if self.verbose:
            log_success("암호화 완료")
        
        return {
            'user_id': self.user_id,
            'pw': '',
            'pw_enc': pw_enc,
            'encsymka': encsymka,
            'c_r_t': self.csrf_token,
            'user_id_enc': '',
        }
    
    def login(self, service: str = 'msi') -> requests.Session:
        """
        SSO 로그인 수행
        
        Args:
            service: 로그인할 서비스 ('lms', 'portal', 'library', 'msi', 'myicap')
        
        Returns:
            requests.Session: 로그인된 세션 객체
        
        Raises:
            InvalidCredentialsError: 로그인 정보가 틀렸을 때
            PageParsingError: 로그인 페이지 파싱에 실패했을 때
            NetworkError: 네트워크 요청에 실패했을 때
            MjuUnivAuthError: 그 외 알 수 없는 에러
        """
        if service not in self.SERVICES:
            raise MjuUnivAuthError(f'Unknown service: {service}')
        
        service_info = self.SERVICES[service]
        
        if self.verbose:
            log_section(f"MJU SSO 로그인: {service_info['name']}")
            print(f"  User ID: {mask_sensitive(self.user_id)}")
        
        # Step 1: 로그인 페이지 접속
        if self.verbose:
            log_step("1-1", "로그인 페이지 접속 (GET)")
        
        login_url = service_info['url']
        
        if self.verbose:
            log_request('GET', login_url)
        
        try:
            response = self.session.get(login_url, timeout=10)
            if self.verbose:
                log_response(response)
        except requests.RequestException as e:
            raise NetworkError(f"페이지 접속 실패: {e}") from e
        
        # 페이지 파싱
        self._parse_login_page(response.text)
        
        # Step 2: 암호화 데이터 준비
        encrypted_data = self._prepare_encrypted_data()
        
        # Step 3: 로그인 요청
        if self.verbose:
            log_step("3", "로그인 요청 전송 (POST)")
        
        if self.form_action.startswith('/'):
            action_url = f"https://sso.mju.ac.kr{self.form_action}"
        else:
            action_url = self.form_action
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://sso.mju.ac.kr',
            'Referer': login_url,
            'Upgrade-Insecure-Requests': '1',
        }
        
        if self.verbose:
            log_request('POST', action_url, headers, encrypted_data)
        
        try:
            response = self.session.post(
                action_url, 
                data=encrypted_data, 
                headers=headers,
                allow_redirects=True,
                timeout=15
            )
            if self.verbose:
                log_response(response)
            
            # JavaScript 폼 제출 및 리다이렉트 처리 (최대 3회 - MSI 로그인에 필요한 실제 횟수)
            for i in range(2):
                # JavaScript 폼 자동 제출 처리 (onLoad="doLogin()" 등)
                form_handled = self._handle_js_form_submit(response, i)
                if form_handled:
                    response = form_handled
                    if self.verbose:
                        log_response(response)
                    continue
                
                # location.href 리다이렉트 처리
                js_redirect_match = re.search(r"location\.href\s*=\s*['\"](.*?)['\"]", response.text)
                if js_redirect_match:
                    redirect_url = js_redirect_match.group(1)
                    if redirect_url.startswith('http'):
                        if self.verbose:
                            log_step(f"3-{i+2}", "JS 리다이렉트 따라가기")
                            log_info("JS Redirect URL", redirect_url, 4)
                        response = self.session.get(redirect_url, allow_redirects=True, timeout=15)
                        if self.verbose:
                            log_response(response)
                        continue
                
                # 더 이상 처리할 JS 동작이 없음
                break
                        
        except requests.RequestException as e:
            raise NetworkError(f"로그인 요청 실패: {e}") from e
        
        # Step 4: 결과 확인
        if self.verbose:
            log_step("4", "로그인 결과 확인")
        
        final_url = response.url
        success_domain = service_info['success_domain']
        
        # 에러 메시지 확인 - var errorMsg = "..." 패턴
        error_msg = None
        var_error_match = re.search(r'var errorMsg = "([^"]+)"', response.text)
        if var_error_match:
            error_msg = var_error_match.group(1)
            try:
                # Unicode escape 디코딩
                error_msg = error_msg.encode('utf-8').decode('unicode_escape')
            except:
                pass
        
        # alert() 패턴도 확인
        if not error_msg:
            alert_match = re.search(r"alert\('(.+?)'\)", response.text)
            if not alert_match:
                alert_match = re.search(r'alert\("(.+?)"\)', response.text)
            if alert_match:
                error_msg = alert_match.group(1)
                try:
                    error_msg = error_msg.encode('utf-8').decode('unicode_escape')
                except:
                    pass
        
        # 로그인 폼이 다시 나타났는지 확인 (실패 시 폼이 다시 표시됨)
        has_signin_form = 'signin-form' in response.text and 'input-password' in response.text
        
        # 실제 대상 도메인으로 이동했는지 확인 (URL 파싱)
        from urllib.parse import urlparse
        parsed_url = urlparse(final_url)
        actually_redirected = success_domain in parsed_url.netloc
        
        # 로그아웃 버튼이 있는지 확인 (로그인 상태 표시)
        has_logout_button = '로그아웃' in response.text or 'logout' in response.text.lower()
        
        # 성공 판정:
        # 1. 실제 대상 도메인으로 이동했고 로그인 폼이 없는 경우
        # 2. 또는 로그아웃 버튼이 있는 경우
        if (actually_redirected and not has_signin_form) or (has_logout_button and not has_signin_form):
            if self.verbose:
                log_success(f"로그인 성공! ({service_info['name']})")
            
            return self.session
        
        # 에러 메시지가 있으면 실패
        if error_msg:
            if self.verbose:
                log_error("로그인 실패")
                log_info("Server Error", error_msg, 4)
            raise InvalidCredentialsError(error_msg)
        
        # 폼이 다시 나타났으면 실패
        if has_signin_form:
            if self.verbose:
                log_error("로그인 실패")
                log_info("원인", "로그인 폼이 다시 표시됨 (인증 실패)", 4)
            raise InvalidCredentialsError('인증 실패 (로그인 정보를 확인해주세요)')
        
        # 알 수 없는 상태
        if self.verbose:
            log_warning("로그인 결과 불확실")
        
        raise MjuUnivAuthError('알 수 없는 오류가 발생했습니다.')
    
    def test_session(self, service: str = 'msi') -> bool:
        """세션 유효성 테스트"""
        service_info = self.SERVICES.get(service, {})
        test_url = service_info.get('test_url')
        
        if not test_url:
            return False
        
        if self.verbose:
            log_step("5", "세션 유효성 테스트")
            log_info("Test URL", test_url)
        
        try:
            response = self.session.get(test_url, timeout=10, allow_redirects=True)
            
            if self.verbose:
                log_info("응답 상태", response.status_code)
                log_info("최종 URL", response.url)
            
            # SSO 또는 login_security로 리다이렉트되면 세션 만료
            if 'sso.mju.ac.kr' in response.url or 'login_security' in response.url:
                if self.verbose:
                    log_warning("세션이 유효하지 않음 (로그인 페이지로 리다이렉트)")
                return False
            
            # 로그아웃 버튼이 있으면 유효한 세션
            if '로그아웃' in response.text or 'logout' in response.text.lower():
                if self.verbose:
                    log_success("세션 유효함")
                return True
            
            if self.verbose:
                log_warning("세션 상태 불확실")
            return False
            
        except requests.RequestException as e:
            log_error(f"테스트 실패: {e}")
            return False