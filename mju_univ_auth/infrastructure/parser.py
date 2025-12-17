"""
HTML 파서 모듈
=============
HTML 파싱 로직을 통합하여 일관된 방식으로 데이터를 추출합니다.
"""

import re
from typing import Optional, Dict, Tuple

from bs4 import BeautifulSoup, SoupStrainer


class HTMLParser:
    """HTML 파싱 유틸리티"""
    
    # CSRF 토큰 추출 패턴들
    CSRF_PATTERNS = [
        # meta 태그
        (r'meta[^>]*_csrf[^>]*content="([^"]+)"', 'meta'),
        # X-CSRF-TOKEN 헤더 설정 (JavaScript 내)
        (r"X-CSRF-TOKEN[\"']?\s*:\s*[\"']([^\"']+)[\"']", 'header'),
        # input hidden 태그
        (r'name="_csrf"\s+value="([^"]+)"', 'input'),
        # value가 먼저 오는 패턴
        (r'value="([^"]+)"[^>]*name="_csrf"', 'input_reverse'),
    ]
    
    @classmethod
    def extract_csrf_token(cls, html: str) -> Optional[str]:
        """HTML에서 CSRF 토큰 추출 (여러 패턴 시도)"""
        for pattern, _ in cls.CSRF_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def extract_login_page_data(cls, html: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        로그인 페이지에서 공개키, CSRF 토큰, 폼 액션 URL 추출
        
        Returns:
            Tuple[public_key, csrf_token, form_action]
        """
        # 정규표현식으로 빠른 추출 시도
        public_key_match = re.search(
            r'value=["\']([^"\']+)["\'][^>]*id=["\']public-key["\']', html
        )
        csrf_match = re.search(
            r'value=["\']([^"\']+)["\'][^>]*id=["\']c_r_t["\']', html
        )
        form_action_match = re.search(
            r'<form[^>]*id=["\']signin-form["\'][^>]*action=["\']([^"\']+)["\']', html
        )
        
        if public_key_match and csrf_match and form_action_match:
            return (
                public_key_match.group(1),
                csrf_match.group(1),
                form_action_match.group(1)
            )
        
        # 정규표현식 실패 시 BeautifulSoup으로 폴백
        parse_only = SoupStrainer(['input', 'form'])
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        
        public_key = None
        csrf_token = None
        form_action = None
        
        public_key_input = soup.find('input', {'id': 'public-key'})
        if public_key_input:
            public_key = public_key_input.get('value')
        
        csrf_input = soup.find('input', {'id': 'c_r_t'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
        
        form = soup.find('form', {'id': 'signin-form'})
        if form:
            form_action = form.get('action')
        
        return public_key, csrf_token, form_action
    
    @classmethod
    def extract_form_data(cls, html: str, form_selector: Optional[str] = None) -> Tuple[Optional[str], Dict[str, str]]:
        """
        HTML에서 폼 액션 URL과 데이터 추출
        
        Args:
            html: HTML 문자열
            form_selector: 폼 선택자 (없으면 첫 번째 폼)
        
        Returns:
            Tuple[action_url, form_data_dict]
        """
        # 정규표현식으로 빠른 추출 시도
        form_action_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', html)
        if not form_action_match:
            return None, {}
        
        action = form_action_match.group(1)
        
        # hidden input들 추출
        input_pattern = re.compile(
            r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']|'
            r'<input[^>]*value=["\']([^"\']*)["\'][^>]*name=["\']([^"\']+)["\']'
        )
        
        form_data = {}
        for match in input_pattern.finditer(html):
            if match.group(1):
                form_data[match.group(1)] = match.group(2)
            elif match.group(4):
                form_data[match.group(4)] = match.group(3)
        
        if not form_data:
            # 정규표현식 실패 시 BeautifulSoup으로 폴백
            parse_only = SoupStrainer('form')
            soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
            form = soup.find('form')
            if form:
                for input_tag in form.find_all('input'):
                    name = input_tag.get('name')
                    value = input_tag.get('value', '')
                    if name:
                        form_data[name] = value
        
        return action, form_data
    
    @classmethod
    def extract_error_message(cls, html: str) -> Optional[str]:
        """HTML에서 에러 메시지 추출"""
        # var errorMsg = "..." 패턴
        var_error_match = re.search(r'var errorMsg = "([^"]+)"', html)
        if var_error_match:
            message = var_error_match.group(1)
            return message.encode('latin-1').decode('unicode_escape')

        # alert() 패턴
        alert_match = re.search(r"alert\(['\"](.+?)['\"]\)", html)
        if alert_match:
            message = alert_match.group(1)
            return message.encode('latin-1').decode('unicode_escape')

        return None
    
    @classmethod
    def extract_js_redirect(cls, html: str) -> Optional[str]:
        """JavaScript 리다이렉트 URL 추출

        다음과 같은 패턴을 지원합니다:
        - location.href = '/path' 또는 'https://...'
        - window.location = '/path' 또는 'https://...'
        - location.replace('/path') 또는 location.assign('/path')
        반환된 값은 절대 또는 상대 URL일 수 있습니다; 필요한 경우 호출자가
        응답 URL로 이를 해결해야 합니다.
        """
        # location.replace('/path') 또는 location.assign('/path') 또는 location.href = '...'
        patterns = [
            r"(?:location|window\.location)\.href\s*=\s*['\"](?P<url>[^'\"]+)['\"]",
            r"(?:location|window\.location)\s*=\s*['\"](?P<url>[^'\"]+)['\"]",
            # r"(?:location\.replace|location\.assign)\s*\(\s*['\"](?P<url>[^'\"]+)['\"]\s*\)",
            # r"window\.location\.replace\(\s*['\"](?P<url>[^'\"]+)['\"]\s*\)",
        ]

        for pat in patterns:
            match = re.search(pat, html)
            if match:
                return match.group('url')

        return None
    
    @classmethod
    def has_js_form_submit(cls, html: str) -> bool:
        """JavaScript 자동 폼 제출 패턴 감지"""
        return 'onLoad=' in html and ('submit()' in html or 'doLogin()' in html)
    
    @classmethod
    def has_signin_form(cls, html: str) -> bool:
        """로그인 폼 존재 여부 확인"""
        return 'signin-form' in html
    
    @classmethod
    def has_logout_button(cls, html: str) -> bool:
        """로그아웃 버튼 존재 여부 확인"""
        return '로그아웃' in html or 'logout' in html.lower()
