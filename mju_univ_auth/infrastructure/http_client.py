"""
HTTP 클라이언트 모듈
===================
requests 세션을 추상화하여 테스트 가능하고 일관된 HTTP 요청을 처리합니다.
"""

from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests

from ..config.settings import DEFAULT_HEADERS, TIMEOUT_CONFIG
from ..exceptions import NetworkError


class HTTPClient:
    """HTTP 클라이언트 - requests.Session 래퍼"""
    
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Args:
            session: 기존 세션 (주입) 또는 None (새로 생성)
        """
        self._session = session or requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
    
    @property
    def session(self) -> requests.Session:
        """내부 requests.Session 접근 (하위 호환성)"""
        return self._session
    
    @property
    def cookies(self) -> requests.cookies.RequestsCookieJar:
        """쿠키 접근"""
        return self._session.cookies
    
    def get(
        self,
        url: str,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> requests.Response:
        """GET 요청"""
        timeout = timeout or TIMEOUT_CONFIG.default
        try:
            return self._session.get(
                url,
                timeout=timeout,
                allow_redirects=allow_redirects,
                **kwargs
            )
        except requests.RequestException as e:
            raise NetworkError(f"GET 요청 실패: {url}", url=url, original_error=e) from e
    
    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> requests.Response:
        """POST 요청"""
        timeout = timeout or TIMEOUT_CONFIG.default
        try:
            return self._session.post(
                url,
                data=data,
                headers=headers,
                timeout=timeout,
                allow_redirects=allow_redirects,
                **kwargs
            )
        except requests.RequestException as e:
            raise NetworkError(f"POST 요청 실패: {url}", url=url, original_error=e) from e
    
    def build_absolute_url(self, base_url: str, path: str) -> str:
        """상대 경로를 절대 URL로 변환"""
        if path.startswith('http'):
            return path
        return urljoin(base_url, path)
    
    def get_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        from urllib.parse import urlparse
        return urlparse(url).netloc
