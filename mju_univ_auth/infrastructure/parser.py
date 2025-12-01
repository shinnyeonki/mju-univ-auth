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
            error_msg = var_error_match.group(1)
            try:
                return error_msg.encode('utf-8').decode('unicode_escape')
            except Exception:
                return error_msg
        
        # alert() 패턴
        alert_match = re.search(r"alert\(['\"](.+?)['\"]\)", html)
        if alert_match:
            error_msg = alert_match.group(1)
            try:
                return error_msg.encode('utf-8').decode('unicode_escape')
            except Exception:
                return error_msg
        
        return None
    
    @classmethod
    def extract_js_redirect(cls, html: str) -> Optional[str]:
        """JavaScript 리다이렉트 URL 추출"""
        match = re.search(r"location\.href\s*=\s*['\"](https?://[^'\"]+)['\"]", html)
        return match.group(1) if match else None
    
    @classmethod
    def has_js_form_submit(cls, html: str) -> bool:
        """JavaScript 자동 폼 제출 패턴 감지"""
        return 'onLoad=' in html and ('submit()' in html or 'doLogin()' in html)
    
    @classmethod
    def has_signin_form(cls, html: str) -> bool:
        """로그인 폼 존재 여부 확인"""
        return 'signin-form' in html and 'input-password' in html
    
    @classmethod
    def has_logout_button(cls, html: str) -> bool:
        """로그아웃 버튼 존재 여부 확인"""
        return '로그아웃' in html or 'logout' in html.lower()
    
    #Modification : 학생카드나 학적 변동 내역의 경우 세부적이 파싱이므로 분리해서 studentCardService 에서 처리하는 것이 맞지 않을까?
    @classmethod
    def parse_student_card_fields(cls, html: str) -> Dict[str, str]:
        """학생카드 HTML에서 필드 추출"""
        parse_only = SoupStrainer(['img', 'div', 'input'])
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        
        fields = {}
        
        # 사진 추출
        img_tag = soup.find('img', src=re.compile(r'^data:image'))
        if img_tag:
            src = img_tag.get('src', '')
            if 'base64,' in src:
                fields['photo_base64'] = src.split('base64,')[1]
        
        # flex-table-item 에서 필드 추출
        for item in soup.find_all('div', class_='flex-table-item'):
            title_div = item.find('div', class_='item-title')
            data_div = item.find('div', class_='item-data')
            
            if not title_div or not data_div:
                continue
            
            title = title_div.get_text(strip=True)
            input_field = data_div.find('input')
            value = input_field.get('value', '') if input_field else data_div.get_text(strip=True)
            
            fields[title] = value
            
            # 특수 처리가 필요한 필드들
            if title == '전화번호':
                tel_input = data_div.find('input', {'name': 'std_tel'})
                if tel_input:
                    fields['phone'] = tel_input.get('value', '')
            elif title == '휴대폰':
                mobile_input = data_div.find('input', {'name': 'htel'})
                if mobile_input:
                    fields['mobile'] = mobile_input.get('value', '')
            elif title == 'E-Mail':
                email_input = data_div.find('input', {'name': 'email'})
                if email_input:
                    fields['email'] = email_input.get('value', '')
            elif '현거주지' in title:
                zip1 = data_div.find('input', {'name': 'zip1'})
                zip2 = data_div.find('input', {'name': 'zip2'})
                if zip1 and zip2:
                    fields['current_zip'] = f"{zip1.get('value', '')}-{zip2.get('value', '')}"
                addr1 = data_div.find('input', {'name': 'addr1'})
                addr2 = data_div.find('input', {'name': 'addr2'})
                if addr1:
                    fields['current_address1'] = addr1.get('value', '')
                if addr2:
                    fields['current_address2'] = addr2.get('value', '')
            elif '주민등록' in title:
                zip1_2 = data_div.find('input', {'name': 'zip1_2'})
                zip2_2 = data_div.find('input', {'name': 'zip2_2'})
                if zip1_2 and zip2_2:
                    fields['registered_zip'] = f"{zip1_2.get('value', '')}-{zip2_2.get('value', '')}"
                addr1_2 = data_div.find('input', {'name': 'addr1_2'})
                addr2_2 = data_div.find('input', {'name': 'addr2_2'})
                if addr1_2:
                    fields['registered_address1'] = addr1_2.get('value', '')
                if addr2_2:
                    fields['registered_address2'] = addr2_2.get('value', '')
            elif '명지포커스' in title:
                checkbox = data_div.find('input', {'name': 'focus_yn'})
                fields['focus_newsletter'] = checkbox and checkbox.get('checked') is not None
        
        return fields
    
    @classmethod
    def parse_change_log_fields(cls, html: str) -> Dict[str, str]:
        """학적변동내역 HTML에서 필드 추출"""
        parse_only = SoupStrainer('div', class_='flex-table-item')
        soup = BeautifulSoup(html, 'lxml', parse_only=parse_only)
        
        fields = {}
        
        for item in soup.find_all('div', class_='flex-table-item'):
            title_div = item.find('div', class_='item-title')
            data_div = item.find('div', class_='item-data')
            
            if not title_div or not data_div:
                continue
            
            title = title_div.get_text(strip=True)
            value = data_div.get_text(strip=True)
            fields[title] = value
        
        return fields
