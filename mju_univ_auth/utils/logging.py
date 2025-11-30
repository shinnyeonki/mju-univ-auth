"""
로깅 모듈
=========
콘솔 출력, 로깅 유틸리티를 제공합니다.
verbose 파라미터를 사용하는 대신 Logger 객체를 통해 일관된 로깅을 수행합니다.
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


class Colors:
    """터미널 색상 코드"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class Logger(ABC):
    """로거 추상 클래스"""
    
    @abstractmethod
    def section(self, title: str) -> None:
        """섹션 구분선 출력"""
        pass
    
    @abstractmethod
    def step(self, step_num: str, title: str) -> None:
        """단계 출력"""
        pass
    
    @abstractmethod
    def info(self, label: str, value: Any, indent: int = 2) -> None:
        """정보 출력"""
        pass
    
    @abstractmethod
    def success(self, message: str) -> None:
        """성공 메시지"""
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        """에러 메시지"""
        pass
    
    @abstractmethod
    def warning(self, message: str) -> None:
        """경고 메시지"""
        pass
    
    @abstractmethod
    def request(self, method: str, url: str, headers: Optional[Dict] = None, data: Optional[Dict] = None) -> None:
        """HTTP 요청 로깅"""
        pass
    
    @abstractmethod
    def response(self, response: Any, show_body: bool = False) -> None:
        """HTTP 응답 로깅"""
        pass


class ConsoleLogger(Logger):
    """콘솔 출력 로거"""
    
    def section(self, title: str) -> None:
        print(f"\n{Colors.HEADER}{'='*70}")
        print(f" {title}")
        print(f"{'='*70}{Colors.END}\n")
    
    def step(self, step_num: str, title: str) -> None:
        print(f"{Colors.BOLD}{Colors.BLUE}[Step {step_num}] {title}{Colors.END}")
    
    def info(self, label: str, value: Any, indent: int = 2) -> None:
        spaces = ' ' * indent
        if isinstance(value, dict):
            print(f"{spaces}{Colors.CYAN}{label}:{Colors.END}")
            for k, v in value.items():
                # 민감 정보 마스킹
                if 'password' in k.lower() or 'pw' in k.lower():
                    v = '****' if v else '(empty)'
                print(f"{spaces}  {k}: {v}")
        elif isinstance(value, str) and len(value) > 100:
            print(f"{spaces}{Colors.CYAN}{label}:{Colors.END} {value[:50]}...({len(value)} chars)")
        else:
            print(f"{spaces}{Colors.CYAN}{label}:{Colors.END} {value}")
    
    def success(self, message: str) -> None:
        print(f"{Colors.GREEN}✓ {message}{Colors.END}")
    
    def error(self, message: str) -> None:
        print(f"{Colors.RED}✗ {message}{Colors.END}")
    
    def warning(self, message: str) -> None:
        print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")
    
    def request(self, method: str, url: str, headers: Optional[Dict] = None, data: Optional[Dict] = None) -> None:
        print(f"\n{Colors.YELLOW}>>> {method} Request >>>{Colors.END}")
        self.info("URL", url)
        if headers:
            important_headers = {k: v for k, v in headers.items() 
                              if k.lower() in ['content-type', 'origin', 'referer', 'cookie']}
            if important_headers:
                self.info("Headers", important_headers)
        if data:
            safe_data = {k: ('****' if 'pw' in k.lower() and v else v) for k, v in data.items()}
            self.info("Form Data", safe_data)
    
    def response(self, response: Any, show_body: bool = False, max_body_length: int = 2000) -> None:
        print(f"\n{Colors.YELLOW}<<< Response <<<{Colors.END}")
        self.info("Status Code", response.status_code)
        self.info("Final URL", response.url)
        
        # 주요 응답 헤더만 출력
        important_headers = ['Content-Type', 'Location', 'Set-Cookie']
        for header_name in important_headers:
            if header_name in response.headers:
                self.info(header_name, response.headers[header_name], 4)
        
        # 쿠키 출력
        if response.cookies:
            print(f"\n  {Colors.CYAN}[Response Cookies]{Colors.END}")
            self.info("Cookies", dict(response.cookies), 4)
        
        # 응답 본문 출력 (옵션)
        if show_body:
            print(f"\n  {Colors.CYAN}[Response Body]{Colors.END}")
            body = response.text
            if len(body) > max_body_length:
                print(f"    (총 {len(body)} chars, 처음 {max_body_length}자만 표시)")
                print(f"    {'-'*60}")
                print(body[:max_body_length])
                print(f"    ... (생략됨)")
            else:
                print(f"    {'-'*60}")
                print(body)
            print(f"    {'-'*60}")


class NullLogger(Logger):
    """아무것도 출력하지 않는 로거 (verbose=False 대체)"""
    
    def section(self, title: str) -> None:
        pass
    
    def step(self, step_num: str, title: str) -> None:
        pass
    
    def info(self, label: str, value: Any, indent: int = 2) -> None:
        pass
    
    def success(self, message: str) -> None:
        pass
    
    def error(self, message: str) -> None:
        pass
    
    def warning(self, message: str) -> None:
        pass
    
    def request(self, method: str, url: str, headers: Optional[Dict] = None, data: Optional[Dict] = None) -> None:
        pass
    
    def response(self, response: Any, show_body: bool = False) -> None:
        pass


def get_logger(verbose: bool = False) -> Logger:
    """verbose 설정에 따라 적절한 로거 반환"""
    return ConsoleLogger() if verbose else NullLogger()


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """민감한 정보 마스킹"""
    if not text or len(text) <= visible_chars:
        return '****'
    return f"{text[:visible_chars]}****"
