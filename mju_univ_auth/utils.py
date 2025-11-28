"""
로깅 및 공통 유틸리티
====================
콘솔 출력, 로깅, HTTP 요청/응답 로깅 등 공통 기능
"""


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


def log_section(title: str) -> None:
    """섹션 구분선 출력"""
    print(f"\n{Colors.HEADER}{'='*70}")
    print(f" {title}")
    print(f"{'='*70}{Colors.END}\n")


def log_step(step_num: str, title: str) -> None:
    """단계 출력"""
    print(f"{Colors.BOLD}{Colors.BLUE}[Step {step_num}] {title}{Colors.END}")


def log_info(label: str, value, indent: int = 2) -> None:
    """정보 출력"""
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


def log_success(message: str) -> None:
    """성공 메시지"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def log_error(message: str) -> None:
    """에러 메시지"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def log_warning(message: str) -> None:
    """경고 메시지"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def log_request(method: str, url: str, headers: dict = None, data: dict = None) -> None:
    """HTTP 요청 로깅"""
    print(f"\n{Colors.YELLOW}>>> {method} Request >>>{Colors.END}")
    log_info("URL", url)
    if headers:
        important_headers = {k: v for k, v in headers.items() 
                          if k.lower() in ['content-type', 'origin', 'referer', 'cookie']}
        if important_headers:
            log_info("Headers", important_headers)
    if data:
        safe_data = {k: ('****' if 'pw' in k.lower() and v else v) for k, v in data.items()}
        log_info("Form Data", safe_data)


def log_response(response, show_body: bool = False, max_body_length: int = 2000) -> None:
    """HTTP 응답 로깅"""
    print(f"\n{Colors.YELLOW}<<< Response <<<{Colors.END}")
    log_info("Status Code", response.status_code)
    log_info("Final URL", response.url)
    
    # 주요 응답 헤더만 출력
    important_headers = ['Content-Type', 'Location', 'Set-Cookie']
    for header_name in important_headers:
        if header_name in response.headers:
            log_info(header_name, response.headers[header_name], 4)
    
    # 쿠키 출력
    if response.cookies:
        print(f"\n  {Colors.CYAN}[Response Cookies]{Colors.END}")
        log_info("Cookies", dict(response.cookies), 4)
    
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


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """민감한 정보 마스킹"""
    if not text or len(text) <= visible_chars:
        return '****'
    return f"{text[:visible_chars]}****"
