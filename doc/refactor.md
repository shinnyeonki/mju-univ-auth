# mju-univ-auth 리팩토링 문서

> **버전**: 0.4.0  
> **작성일**: 2024년 12월  
> **목적**: 일관성(Consistency), 단순성(Simplicity), 유지보수성(Maintainability) 향상

---

## 목차

1. [리팩토링 배경](#1-리팩토링-배경)
2. [기존 코드의 문제점 분석](#2-기존-코드의-문제점-분석)
3. [새로운 아키텍처 설계](#3-새로운-아키텍처-설계)
4. [계층별 상세 설명](#4-계층별-상세-설명)
5. [설계 원칙과 패턴](#5-설계-원칙과-패턴)
6. [구현 세부사항](#6-구현-세부사항)
7. [마이그레이션 가이드](#7-마이그레이션-가이드)
8. [테스트 전략](#8-테스트-전략)
9. [향후 확장 방향](#9-향후-확장-방향)

---

## 1. 리팩토링 배경

### 1.1 프로젝트 소개

`mju-univ-auth`는 명지대학교 SSO(Single Sign-On) 시스템을 통해 학생 정보를 조회하는 Python 라이브러리입니다. 주요 기능은 다음과 같습니다:

- **SSO 로그인**: LMS, Portal, Library, MSI(My iWeb), MyiCAP 등 다양한 서비스에 로그인
- **학생카드 조회**: 학번, 성명, 학과, 연락처, 주소 등 기본 정보
- **학적변동내역 조회**: 학적상태, 이수학기 등 학적 관련 정보

### 1.2 리팩토링 목표

| 목표 | 설명 |
|------|------|
| **일관성 (Consistency)** | 네이밍 규칙, 코드 스타일, 에러 처리 방식의 통일 |
| **단순성 (Simplicity)** | 각 모듈의 책임을 명확히 분리하여 복잡도 감소 |
| **유지보수성 (Maintainability)** | 테스트 가능한 구조, 설정 외부화, 느슨한 결합 |

### 1.3 리팩토링 범위

- 전체 코드베이스 재구성
- 계층형 아키텍처 도입
- Facade 패턴을 통한 API 단순화
- 의존성 주입(DI) 적용
- 예외 처리 표준화

---

## 2. 기존 코드의 문제점 분석

### 2.1 일관성 (Consistency) 문제

#### 2.1.1 네이밍 컨벤션의 불일치

```python
# 기존 코드의 클래스명 불일치
class _StudentCardFetcher:  # Private, 접두사 사용
    pass

class MJUSSOLogin:  # Public, 접두사 없음
    pass

class BaseFetcher:  # 추상 클래스, 접두사 없음
    pass
```

**문제점**:
- Private 클래스와 Public 클래스의 명명 규칙이 혼재
- `MJU` 접두사가 일부 클래스에만 적용됨
- 역할(Fetcher, Service, Handler)에 대한 일관된 명명 규칙 부재

#### 2.1.2 책임 분리의 불일치

```python
# 기존 StudentCard 클래스 - 데이터와 비즈니스 로직이 혼재
@dataclass
class StudentCard:
    student_id: str = ""
    name_korean: str = ""
    # ... 데이터 필드들
    
    @classmethod
    def fetch(cls, session, user_pw, verbose=False):
        """네트워크 요청을 수행하는 메서드가 데이터 클래스에 존재"""
        fetcher = _StudentCardFetcher(session, user_pw, verbose)
        return fetcher.fetch()
```

**문제점**:
- 데이터 클래스(`StudentCard`)가 네트워크 로직을 알고 있음 (SRP 위반)
- `StudentCard.fetch()` 호출 시 내부적으로 `_StudentCardFetcher`를 생성하는 비직관적 구조
- 데이터 레이어와 서비스 레이어의 경계가 불명확

#### 2.1.3 에러 처리 일관성 부재

```python
# 기존 코드의 에러 처리 - 다양한 방식이 혼재

# 방식 1: requests 예외를 직접 변환
try:
    response = session.get(url)
except requests.RequestException as e:
    raise NetworkError(f"요청 실패: {e}")

# 방식 2: 특정 조건에서 직접 예외 발생
if 'signin-form' in html:
    raise InvalidCredentialsError("인증 실패")

# 방식 3: 예외 없이 None 반환
def extract_csrf(html):
    match = re.search(pattern, html)
    return match.group(1) if match else None  # 실패 시 None
```

**문제점**:
- 에러 발생 조건과 처리 방식이 일관되지 않음
- 예외에 컨텍스트 정보(URL, 상태 코드 등)가 누락됨
- 디버깅 시 에러 원인 파악이 어려움

### 2.2 단순성 (Simplicity) 문제

#### 2.2.1 과도한 복잡도

**기존 sso.py 분석** (461줄):

```python
class MJUSSOLogin:
    def login(self, service='msi'):
        # 1. 로그인 페이지 접속 (GET)
        # 2. 페이지 파싱 (정규표현식 → BeautifulSoup 폴백)
        # 3. 암호화 데이터 준비 (세션키 생성, RSA, AES)
        # 4. 로그인 요청 (POST)
        # 5. JS 폼 자동 제출 처리 (최대 3회 반복)
        # 6. JS 리다이렉트 처리
        # 7. 로그인 성공 판정 (4가지 조건 조합)
        # 8. 에러 메시지 추출 및 처리
        pass
```

**Cyclomatic Complexity 분석**:

| 메서드 | 분기 수 | 복잡도 |
|--------|---------|--------|
| `login()` | 12+ | 높음 |
| `_handle_js_form_submit()` | 8+ | 높음 |
| `_validate_login_result()` | 6+ | 중간 |
| `_parse_login_page()` | 4 | 낮음 |

**문제점**:
- 하나의 메서드가 너무 많은 책임을 가짐
- 조건문 중첩으로 가독성 저하
- 테스트 케이스 작성이 어려움

#### 2.2.2 중복 코드

```python
# CSRF 토큰 추출 로직이 여러 곳에 분산

# sso.py에서
csrf_match = re.search(r'value="([^"]+)"[^>]*id="c_r_t"', html)

# student_card.py에서
csrf_match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)

# student_changelog.py에서
csrf_match = re.search(r'meta[^>]*_csrf[^>]*content="([^"]+)"', html)
```

**문제점**:
- 동일한 기능의 코드가 여러 파일에 존재
- 패턴 변경 시 모든 위치를 찾아 수정해야 함
- 코드 재사용성 부족

#### 2.2.3 과도한 verbose 파라미터 전달

```python
# 모든 메서드에 verbose 파라미터가 전달됨
def login(self, service='msi', verbose=False):
    fetcher = Fetcher(session, verbose=verbose)
    fetcher.fetch(verbose=verbose)
    
    if verbose:
        print(f"[DEBUG] URL: {url}")
        print(f"[DEBUG] Response: {response.status_code}")
```

**문제점**:
- 모든 메서드 시그니처에 `verbose` 파라미터 존재
- 로깅 로직이 비즈니스 로직과 혼재
- 새 메서드 추가 시 항상 `verbose` 처리 필요

### 2.3 유지보수성 (Maintainability) 문제

#### 2.3.1 하드코딩된 URL과 설정

```python
# 기존 코드 - 설정이 코드 곳곳에 분산

class MJUSSOLogin:
    SERVICES = {
        'lms': {
            'name': 'LMS (e-Class)',
            'url': 'https://sso.mju.ac.kr/sso/auth?response_type=code&client_id=lms&...',
            'success_domain': 'lms.mju.ac.kr',
            'test_url': 'https://lms.mju.ac.kr/ilos/main/main_form.acl'
        },
        # ... 5개 서비스가 클래스 내부에 하드코딩
    }

class _StudentCardFetcher:
    STUDENT_CARD_URL = "https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard"
    # URL이 각 클래스에 분산
```

**문제점**:
- URL 변경 시 여러 파일을 수정해야 함
- 환경별(개발/운영) 설정 분리 불가능
- 새 서비스 추가 시 코드 수정 필요

#### 2.3.2 강결합 (Tight Coupling)

```python
# 기존 코드 - 직접적인 의존성

class _StudentCardFetcher:
    def __init__(self, session: requests.Session, ...):
        self.session = session  # requests.Session에 직접 의존
        
    def fetch(self):
        # requests 라이브러리에 직접 의존
        response = self.session.post(url, data=data, timeout=10)
```

**의존성 그래프 (기존)**:

```
StudentCard.fetch()
    └── _StudentCardFetcher
            ├── requests.Session (직접 의존)
            ├── re (정규표현식)
            ├── BeautifulSoup (파싱)
            └── print() (로깅)
```

**문제점**:
- Mock 객체로 대체 불가능 → 단위 테스트 어려움
- `requests` 라이브러리 교체 시 전체 코드 수정 필요
- 관심사 분리 부족

#### 2.3.3 테스트 불가능한 구조

```python
# 기존 코드 - 테스트 작성이 어려운 구조

def test_student_card_fetch():
    # 문제 1: 실제 네트워크 요청 발생
    card = StudentCard.fetch(session, password)
    
    # 문제 2: 로그인 상태에 의존
    # 문제 3: 외부 서버 상태에 의존
    # 문제 4: 파싱 로직과 네트워크 로직이 결합되어 개별 테스트 불가
```

**문제점**:
- 네트워크 요청 Mock 불가능
- 파싱 로직만 독립적으로 테스트 불가
- 테스트 실행 시간이 길고 불안정

---

## 3. 새로운 아키텍처 설계

### 3.1 계층형 아키텍처 (Layered Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│                      (facade.py)                             │
│                      MjuUnivAuth                             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Service Layer                             │
│                     (services/)                              │
│    SSOService  StudentCardService  StudentChangeLogService   │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Domain Layer                               │
│                     (domain/)                                │
│              StudentCard   StudentChangeLog                  │
└─────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                Infrastructure Layer                          │
│                  (infrastructure/)                           │
│          HTTPClient    HTMLParser    Crypto                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                Cross-Cutting Concerns                        │
│              (config/, utils/, exceptions.py)                │
│         Settings    Logger    Custom Exceptions              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 새로운 디렉토리 구조

```
mju_univ_auth/
├── __init__.py              # Public API exports
├── __main__.py              # CLI entry point
├── facade.py                # MjuUnivAuth - 메인 Facade 클래스
├── exceptions.py            # 표준화된 예외 클래스
│
├── config/                  # 설정 관리
│   ├── __init__.py
│   └── settings.py          # ServiceConfig, MSIUrls, TimeoutConfig
│
├── domain/                  # 순수 데이터 모델
│   ├── __init__.py
│   ├── student_card.py      # StudentCard dataclass
│   └── student_changelog.py # StudentChangeLog dataclass
│
├── infrastructure/          # 외부 의존성 추상화
│   ├── __init__.py
│   ├── http_client.py       # HTTPClient - requests 래퍼
│   ├── parser.py            # HTMLParser - 파싱 로직 통합
│   └── crypto.py            # 암호화 유틸리티
│
├── services/                # 비즈니스 로직
│   ├── __init__.py
│   ├── sso_service.py       # SSOService - 로그인 처리
│   ├── student_card_service.py      # StudentCardService
│   └── student_changelog_service.py # StudentChangeLogService
│
└── utils/                   # 공통 유틸리티
    ├── __init__.py
    └── logging.py           # Logger 클래스 (ConsoleLogger, NullLogger)
```

### 3.3 각 계층의 책임

| 계층 | 책임 | 의존성 |
|------|------|--------|
| **Facade** | 사용자 친화적 API 제공, 서비스 조합 | Service Layer |
| **Service** | 비즈니스 로직, 워크플로우 조율 | Domain, Infrastructure |
| **Domain** | 순수 데이터 모델, 비즈니스 규칙 | 없음 (독립적) |
| **Infrastructure** | 외부 시스템 연동 (HTTP, 파싱) | 외부 라이브러리 |
| **Cross-Cutting** | 로깅, 설정, 예외 처리 | 모든 계층에서 사용 |

### 3.4 의존성 방향

```
     ┌─────────┐
     │ Facade  │
     └────┬────┘
          │ depends on
     ┌────▼────┐
     │ Service │
     └────┬────┘
          │ depends on
    ┌─────┴─────┐
    │           │
┌───▼───┐ ┌────▼─────────┐
│Domain │ │Infrastructure│
└───────┘ └──────────────┘
    ↑           │
    │           │ uses
    │     ┌─────▼─────┐
    └─────│  Config   │
          │  Utils    │
          │ Exceptions│
          └───────────┘
```

**핵심 원칙**:
- 상위 계층은 하위 계층에만 의존
- Domain 계층은 다른 계층에 의존하지 않음
- Infrastructure는 외부 라이브러리를 추상화

---

## 4. 계층별 상세 설명

### 4.1 Facade Layer (facade.py)

#### 4.1.1 설계 목적

Facade 패턴은 복잡한 서브시스템에 대한 단순화된 인터페이스를 제공합니다. 사용자는 내부 구조를 알 필요 없이 `MjuUnivAuth` 클래스만 사용하면 됩니다.

#### 4.1.2 구현

```python
class MjuUnivAuth:
    """
    명지대학교 인증 및 정보 조회를 위한 메인 클래스
    
    사용 예시:
        from mju_univ_auth import MjuUnivAuth
        
        auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
        student_card = auth.get_student_card()
    """
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        verbose: bool = False,
    ):
        self.user_id = user_id
        self.user_pw = user_pw
        self.verbose = verbose
        
        # 의존성은 내부에서 생성하되, 테스트 시 교체 가능
        self._logger: Logger = get_logger(verbose)
        self._http_client: Optional[HTTPClient] = None
        self._logged_in_service: Optional[str] = None
    
    def _ensure_login(self, service: str = 'msi') -> HTTPClient:
        """필요 시 로그인 수행 (Lazy Initialization)"""
        if self._http_client and self._logged_in_service == service:
            return self._http_client
        
        sso = SSOService(
            user_id=self.user_id,
            user_pw=self.user_pw,
            http_client=HTTPClient(),
            logger=self._logger,
        )
        
        self._http_client = sso.login(service=service)
        self._logged_in_service = service
        
        return self._http_client
    
    def get_student_card(self, print_summary: bool = False) -> StudentCard:
        """학생카드 정보 조회"""
        http_client = self._ensure_login(service='msi')
        
        service = StudentCardService(
            http_client=http_client,
            user_pw=self.user_pw,
            logger=self._logger,
        )
        
        student_card = service.fetch()
        
        if print_summary:
            student_card.print_summary()
        
        return student_card
```

#### 4.1.3 설계 결정 이유

| 결정 | 이유 |
|------|------|
| **Lazy Initialization** | 불필요한 로그인 방지, 필요 시에만 세션 생성 |
| **세션 재사용** | 동일 서비스 재요청 시 불필요한 재로그인 방지 |
| **Logger 주입** | verbose 파라미터를 각 메서드에 전달하지 않고 Logger 객체로 통합 |
| **Method Chaining** | `auth.login().get_student_card()` 형태 지원 |

### 4.2 Service Layer (services/)

#### 4.2.1 설계 목적

Service Layer는 비즈니스 로직을 담당합니다. 각 서비스는 단일 책임을 가지며, Infrastructure 계층의 컴포넌트를 조합하여 기능을 수행합니다.

#### 4.2.2 SSOService 구현

```python
class SSOService:
    """명지대학교 SSO 로그인 서비스"""
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        http_client: Optional[HTTPClient] = None,
        logger: Optional[Logger] = None,
    ):
        self.user_id = user_id
        self.user_pw = user_pw
        self.http = http_client or HTTPClient()  # 의존성 주입
        self.logger = logger or get_logger(False)
    
    def login(self, service: str = 'msi') -> HTTPClient:
        """SSO 로그인 수행"""
        # Step 1: 로그인 페이지 접속
        self._fetch_login_page(service_config.auth_url)
        
        # Step 2: 암호화 데이터 준비
        encrypted_data = self._prepare_encrypted_data()
        
        # Step 3: 로그인 요청
        response = self._submit_login(service_config.auth_url, encrypted_data)
        
        # Step 4: 리다이렉트 처리
        response = self._handle_redirects(response)
        
        # Step 5: 결과 검증
        self._validate_login_result(response, service_config)
        
        return self.http
```

#### 4.2.3 메서드 분리 전략

**기존 코드**: 하나의 `login()` 메서드에 모든 로직 (461줄)

**새 구조**: 책임별로 메서드 분리

| 메서드 | 책임 | 라인 수 |
|--------|------|---------|
| `_fetch_login_page()` | 페이지 접속 및 파싱 | ~30줄 |
| `_prepare_encrypted_data()` | 암호화 처리 | ~25줄 |
| `_submit_login()` | 로그인 요청 전송 | ~25줄 |
| `_handle_redirects()` | JS 리다이렉트 처리 | ~40줄 |
| `_validate_login_result()` | 결과 검증 | ~35줄 |

**장점**:
- 각 메서드의 복잡도 감소
- 개별 기능 단위 테스트 가능
- 코드 가독성 향상

### 4.3 Domain Layer (domain/)

#### 4.3.1 설계 목적

Domain Layer는 순수 데이터 모델만 포함합니다. 네트워크 요청, 파싱 등의 로직은 포함하지 않으며, 다른 계층에 의존하지 않습니다.

#### 4.3.2 StudentCard 구현

```python
@dataclass
class StudentCard:
    """학생카드 정보 데이터 클래스"""
    
    # 기본 정보
    student_id: str = ""
    name_korean: str = ""
    name_english_first: str = ""
    name_english_last: str = ""
    
    # 학적 정보
    grade: str = ""
    status: str = ""
    department: str = ""
    
    # ... 추가 필드
    
    @property
    def name_english(self) -> str:
        """영문 성명 전체 (계산된 속성)"""
        return f"{self.name_english_first} {self.name_english_last}".strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {...}
    
    @classmethod
    def from_parsed_fields(cls, fields: Dict[str, Any]) -> 'StudentCard':
        """팩토리 메서드: 파싱된 필드에서 객체 생성"""
        card = cls()
        # 필드 매핑 로직
        return card
```

#### 4.3.3 설계 결정 이유

| 결정 | 이유 |
|------|------|
| **@dataclass 사용** | 보일러플레이트 코드 감소, 불변성 옵션 |
| **기본값 지정** | 부분적 데이터 파싱 시에도 객체 생성 가능 |
| **팩토리 메서드** | 복잡한 생성 로직을 캡슐화 |
| **네트워크 로직 제거** | SRP 준수, 테스트 용이성 |

### 4.4 Infrastructure Layer (infrastructure/)

#### 4.4.1 설계 목적

Infrastructure Layer는 외부 시스템(HTTP, 파싱 라이브러리)에 대한 의존성을 추상화합니다. 상위 계층은 구체적인 구현이 아닌 추상화에 의존합니다.

#### 4.4.2 HTTPClient 구현

```python
class HTTPClient:
    """HTTP 클라이언트 - requests.Session 래퍼"""
    
    def __init__(self, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
    
    @property
    def session(self) -> requests.Session:
        """내부 세션 접근 (하위 호환성)"""
        return self._session
    
    def get(
        self,
        url: str,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> requests.Response:
        """GET 요청 - 예외를 NetworkError로 변환"""
        timeout = timeout or TIMEOUT_CONFIG.default
        try:
            return self._session.get(url, timeout=timeout, allow_redirects=allow_redirects, **kwargs)
        except requests.RequestException as e:
            raise NetworkError(f"GET 요청 실패: {url}", url=url, original_error=e) from e
    
    def post(self, url: str, data=None, headers=None, timeout=None, **kwargs):
        """POST 요청"""
        # 동일한 패턴
```

**추상화 장점**:
1. **테스트 용이성**: Mock HTTPClient로 교체 가능
2. **예외 표준화**: `requests.RequestException` → `NetworkError`
3. **기본값 관리**: 타임아웃, 헤더 등을 한 곳에서 관리
4. **라이브러리 교체 용이**: `requests` → `httpx` 등으로 변경 시 이 클래스만 수정

#### 4.4.3 HTMLParser 구현

```python
class HTMLParser:
    """HTML 파싱 유틸리티"""
    
    CSRF_PATTERNS = [
        (r'meta[^>]*_csrf[^>]*content="([^"]+)"', 'meta'),
        (r"X-CSRF-TOKEN[\"']?\s*:\s*[\"']([^\"']+)[\"']", 'header'),
        (r'name="_csrf"\s+value="([^"]+)"', 'input'),
    ]
    
    @classmethod
    def extract_csrf_token(cls, html: str) -> Optional[str]:
        """CSRF 토큰 추출 (여러 패턴 시도)"""
        for pattern, _ in cls.CSRF_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None
    
    @classmethod
    def extract_login_page_data(cls, html: str) -> Tuple[Optional[str], ...]:
        """로그인 페이지 데이터 추출"""
        # 정규표현식으로 빠른 추출 시도
        # 실패 시 BeautifulSoup으로 폴백
```

**설계 결정**:
- **@classmethod 사용**: 상태가 없으므로 인스턴스 불필요
- **이중 파싱 전략**: 정규표현식(빠름) → BeautifulSoup(안정)
- **통합된 인터페이스**: 분산된 파싱 로직을 한 곳에서 관리

### 4.5 Cross-Cutting Concerns

#### 4.5.1 설정 관리 (config/settings.py)

```python
@dataclass(frozen=True)
class ServiceConfig:
    """서비스별 설정 데이터 클래스"""
    name: str
    auth_url: str
    success_domain: str
    test_url: str

SERVICES: Dict[str, ServiceConfig] = {
    'lms': ServiceConfig(
        name='LMS (e-Class)',
        auth_url='https://sso.mju.ac.kr/sso/auth?...',
        success_domain='lms.mju.ac.kr',
        test_url='https://lms.mju.ac.kr/ilos/main/main_form.acl'
    ),
    # ... 다른 서비스들
}

class MSIUrls:
    """MSI 서비스 URL 상수"""
    HOME = "https://msi.mju.ac.kr/servlet/security/MySecurityStart"
    STUDENT_CARD = "https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard"

@dataclass(frozen=True)
class TimeoutConfig:
    """타임아웃 설정"""
    default: int = 10
    login: int = 15
```

**설계 결정**:
- **불변 데이터 클래스**: `frozen=True`로 실수로 인한 변경 방지
- **중앙 집중식 관리**: URL, 타임아웃 등을 한 곳에서 관리
- **서비스 확장 용이**: 새 서비스 추가 시 `SERVICES`에만 추가

#### 4.5.2 로깅 시스템 (utils/logging.py)

```python
class Logger(ABC):
    """로거 추상 클래스"""
    
    @abstractmethod
    def section(self, title: str) -> None:
        pass
    
    @abstractmethod
    def step(self, step_num: str, title: str) -> None:
        pass
    
    @abstractmethod
    def info(self, label: str, value: Any, indent: int = 2) -> None:
        pass
    
    @abstractmethod
    def success(self, message: str) -> None:
        pass
    
    @abstractmethod
    def error(self, message: str) -> None:
        pass

class ConsoleLogger(Logger):
    """실제 출력 로거"""
    def section(self, title: str) -> None:
        print(f"\n{'='*70}")
        print(f" {title}")
        print(f"{'='*70}\n")

class NullLogger(Logger):
    """아무것도 출력하지 않는 로거"""
    def section(self, title: str) -> None:
        pass

def get_logger(verbose: bool = False) -> Logger:
    """팩토리 함수"""
    return ConsoleLogger() if verbose else NullLogger()
```

**Null Object 패턴**:
- `verbose=False`일 때 `NullLogger` 반환
- 조건문 없이 로깅 메서드 호출 가능
- 코드 가독성 향상

#### 4.5.3 예외 처리 (exceptions.py)

```python
class MjuUnivAuthError(Exception):
    """기본 예외 클래스"""
    
    def __init__(self, message: str, **context):
        super().__init__(message)
        self.message = message
        self.context = context
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message

class NetworkError(MjuUnivAuthError):
    """네트워크 오류"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
        **context
    ):
        super().__init__(message, **context)
        self.url = url
        self.status_code = status_code
        self.original_error = original_error
```

**예외 계층 구조**:

```
MjuUnivAuthError (기본)
├── NetworkError (네트워크)
├── PageParsingError (파싱)
├── InvalidCredentialsError (인증)
├── SessionExpiredError (세션)
└── ServiceNotFoundError (서비스)
```

**컨텍스트 정보 포함**:
```python
# 기존
raise Exception("로그인 실패")

# 개선
raise InvalidCredentialsError(
    "로그인 실패",
    service="msi",
    url="https://sso.mju.ac.kr/...",
    attempted_id="60123456"
)
```

---

## 5. 설계 원칙과 패턴

### 5.1 SOLID 원칙 적용

#### 5.1.1 단일 책임 원칙 (SRP)

**기존 위반 사례**:
```python
class StudentCard:
    # 데이터 저장 + 네트워크 요청 + 파싱
    @classmethod
    def fetch(cls, session, user_pw, verbose):
        fetcher = _StudentCardFetcher(session, user_pw, verbose)
        return fetcher.fetch()
```

**개선**:
```python
# 데이터만 담당
class StudentCard:
    student_id: str
    name_korean: str

# 조회 로직 담당
class StudentCardService:
    def fetch(self) -> StudentCard:
        pass

# 파싱 로직 담당
class HTMLParser:
    @classmethod
    def parse_student_card_fields(cls, html: str) -> Dict:
        pass
```

#### 5.1.2 개방-폐쇄 원칙 (OCP)

**새 서비스 추가 시**:

```python
# settings.py에 설정만 추가
SERVICES['new_service'] = ServiceConfig(
    name='New Service',
    auth_url='https://...',
    success_domain='new.mju.ac.kr',
    test_url='https://new.mju.ac.kr/...'
)

# 기존 코드 수정 없이 사용 가능
auth.login(service='new_service')
```

#### 5.1.3 의존성 역전 원칙 (DIP)

```python
# 추상화에 의존
class SSOService:
    def __init__(
        self,
        http_client: HTTPClient,  # 구체 클래스가 아닌 인터페이스
        logger: Logger,           # 추상 클래스
    ):
        self.http = http_client
        self.logger = logger
```

### 5.2 적용된 디자인 패턴

#### 5.2.1 Facade 패턴

**목적**: 복잡한 서브시스템에 단순한 인터페이스 제공

```python
# 복잡한 내부 구조
class SSOService: ...
class StudentCardService: ...
class HTTPClient: ...
class HTMLParser: ...

# 단순한 외부 인터페이스
class MjuUnivAuth:
    def get_student_card(self) -> StudentCard:
        # 내부에서 복잡한 조합 처리
```

#### 5.2.2 Factory 패턴

```python
# Logger 팩토리
def get_logger(verbose: bool) -> Logger:
    return ConsoleLogger() if verbose else NullLogger()

# StudentCard 팩토리 메서드
@classmethod
def from_parsed_fields(cls, fields: Dict) -> 'StudentCard':
    # 복잡한 생성 로직 캡슐화
```

#### 5.2.3 Null Object 패턴

```python
class NullLogger(Logger):
    """아무 동작도 하지 않는 로거"""
    def info(self, label, value, indent=2):
        pass  # 아무것도 안 함

# 사용 시
self.logger.info("URL", url)  # verbose 여부 확인 불필요
```

#### 5.2.4 Strategy 패턴 (암묵적)

```python
# 정규표현식 전략 → BeautifulSoup 전략으로 폴백
@classmethod
def extract_login_page_data(cls, html: str):
    # 전략 1: 정규표현식 (빠름)
    result = cls._try_regex_extraction(html)
    if result:
        return result
    
    # 전략 2: BeautifulSoup (안정)
    return cls._try_beautifulsoup_extraction(html)
```

### 5.3 의존성 주입 (Dependency Injection)

#### 5.3.1 생성자 주입

```python
class SSOService:
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        http_client: Optional[HTTPClient] = None,  # 주입 가능
        logger: Optional[Logger] = None,           # 주입 가능
    ):
        self.http = http_client or HTTPClient()    # 기본값 제공
        self.logger = logger or get_logger(False)
```

#### 5.3.2 테스트에서의 활용

```python
def test_sso_login_success():
    # Mock 객체 주입
    mock_http = MockHTTPClient()
    mock_http.responses = [
        MockResponse(200, "<html>login page...</html>"),
        MockResponse(302, location="https://msi.mju.ac.kr/...")
    ]
    
    sso = SSOService(
        user_id="test",
        user_pw="test",
        http_client=mock_http,
        logger=NullLogger()
    )
    
    result = sso.login()
    assert result is not None
```

---

## 6. 구현 세부사항

### 6.1 파일별 라인 수 비교

| 파일 | 기존 | 개선 | 변화 |
|------|------|------|------|
| sso.py / sso_service.py | 461줄 | 288줄 | ↓37% |
| student_card.py | 382줄 | 173줄(도메인) + 207줄(서비스) | 분리 |
| student_changelog.py | 183줄 | 58줄(도메인) + 124줄(서비스) | 분리 |
| crypto.py | 166줄 | 117줄 | ↓30% |
| **신규 파일** | - | - | - |
| facade.py | - | 180줄 | 신규 |
| http_client.py | - | 88줄 | 신규 |
| parser.py | - | 264줄 | 신규 |
| settings.py | - | 82줄 | 신규 |
| logging.py | - | 182줄 | 신규 |
| exceptions.py | 30줄 | 107줄 | 확장 |

### 6.2 주요 변경 사항

#### 6.2.1 로그인 성공 판정 로직 개선

**기존 문제**:
```python
# 에러 메시지가 있으면 무조건 실패 처리
error_msg = self._extract_error_message(html)
if error_msg:
    raise InvalidCredentialsError(error_msg)
```

**개선**:
```python
def _validate_login_result(self, response, service_config):
    # 성공 조건을 먼저 검사
    if (actually_redirected and not has_signin_form) or \
       (has_logout and not has_signin_form):
        return  # 성공
    
    # 그 다음 실패 조건 검사
    if has_signin_form:
        error_msg = HTMLParser.extract_error_message(html)
        raise InvalidCredentialsError(error_msg or "인증 실패")
```

#### 6.2.2 CSRF 토큰 추출 통합

**기존**: 각 파일에서 다른 패턴 사용

**개선**: `HTMLParser`에서 모든 패턴 시도

```python
class HTMLParser:
    CSRF_PATTERNS = [
        (r'meta[^>]*_csrf[^>]*content="([^"]+)"', 'meta'),
        (r"X-CSRF-TOKEN[\"']?\s*:\s*[\"']([^\"']+)[\"']", 'header'),
        (r'name="_csrf"\s+value="([^"]+)"', 'input'),
        (r'value="([^"]+)"[^>]*name="_csrf"', 'input_reverse'),
    ]
    
    @classmethod
    def extract_csrf_token(cls, html: str) -> Optional[str]:
        for pattern, _ in cls.CSRF_PATTERNS:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None
```

#### 6.2.3 .env 파일 로드 지원

```python
# __main__.py
from dotenv import load_dotenv

def main():
    load_dotenv()  # .env 파일 자동 로드
    
    user_id = os.getenv('MJU_ID')
    user_pw = os.getenv('MJU_PW')
```

### 6.3 에러 처리 흐름

```
사용자 요청
    │
    ▼
MjuUnivAuth.get_student_card()
    │
    ├──→ NetworkError: 네트워크 연결 실패
    │
    ├──→ InvalidCredentialsError: 로그인 정보 오류
    │
    ├──→ SessionExpiredError: 세션 만료
    │
    ├──→ PageParsingError: HTML 파싱 실패
    │
    └──→ MjuUnivAuthError: 기타 오류
```

---

## 7. 마이그레이션 가이드

### 7.1 API 변경 사항

#### 7.1.1 기존 API

```python
# 기존 사용법
from mju_univ_auth import MJUSSOLogin, StudentCard

# SSO 로그인
sso = MJUSSOLogin(user_id="학번", user_pw="비밀번호")
session = sso.login(service='msi', verbose=True)

# 학생카드 조회
student_card = StudentCard.fetch(session, user_pw="비밀번호", verbose=True)
print(student_card.name_korean)
```

#### 7.1.2 새 API

```python
# 새 사용법
from mju_univ_auth import MjuUnivAuth

# 통합 인터페이스
auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호", verbose=True)

# 학생카드 조회 (로그인 자동 처리)
student_card = auth.get_student_card()
print(student_card.name_korean)
```

### 7.2 변경 매핑 테이블

| 기존 | 새 | 비고 |
|------|-----|------|
| `MJUSSOLogin` | `MjuUnivAuth` | Facade로 통합 |
| `StudentCard.fetch()` | `auth.get_student_card()` | 메서드 이동 |
| `StudentChangeLog.fetch()` | `auth.get_student_changelog()` | 메서드 이동 |
| `verbose=True` (매개변수) | 생성자에서 한 번만 | Logger로 통합 |
| `session.login()` 반환값 | 내부 관리 | 직접 세션 접근 불필요 |

### 7.3 하위 호환성

```python
# 기존 코드 지원을 위한 import alias 제공
from mju_univ_auth import (
    MjuUnivAuth,      # 새 API
    StudentCard,       # 데이터 클래스 (변경 없음)
    StudentChangeLog,  # 데이터 클래스 (변경 없음)
)
```

---

## 8. 테스트 전략

### 8.1 테스트 피라미드

```
        /\
       /  \     E2E Tests (소수)
      /────\    - 실제 서버 연동 테스트
     /      \
    /────────\  Integration Tests (중간)
   /          \ - 서비스 간 연동 테스트
  /────────────\
 /              \ Unit Tests (다수)
/────────────────\ - 파서, 암호화, 유틸리티
```

### 8.2 단위 테스트 예시

#### 8.2.1 HTMLParser 테스트

```python
def test_extract_csrf_token_from_meta():
    html = '<meta name="_csrf" content="abc123">'
    assert HTMLParser.extract_csrf_token(html) == "abc123"

def test_extract_csrf_token_from_input():
    html = '<input name="_csrf" value="def456">'
    assert HTMLParser.extract_csrf_token(html) == "def456"

def test_extract_csrf_token_not_found():
    html = '<html><body>no csrf</body></html>'
    assert HTMLParser.extract_csrf_token(html) is None
```

#### 8.2.2 암호화 테스트

```python
def test_generate_session_key():
    key_info = generate_session_key(32)
    
    assert 'keyStr' in key_info
    assert 'key' in key_info
    assert 'iv' in key_info
    assert len(key_info['key']) == 32
    assert len(key_info['iv']) == 16
```

### 8.3 Mock을 활용한 서비스 테스트

```python
class MockHTTPClient:
    def __init__(self):
        self.responses = []
        self.request_history = []
    
    def get(self, url, **kwargs):
        self.request_history.append(('GET', url, kwargs))
        return self.responses.pop(0)
    
    def post(self, url, **kwargs):
        self.request_history.append(('POST', url, kwargs))
        return self.responses.pop(0)

def test_sso_service_login():
    mock_http = MockHTTPClient()
    mock_http.responses = [
        MockResponse(200, login_page_html),
        MockResponse(302, redirect_html),
        MockResponse(200, success_html),
    ]
    
    sso = SSOService(
        user_id="test",
        user_pw="test",
        http_client=mock_http,
        logger=NullLogger()
    )
    
    result = sso.login(service='msi')
    
    assert len(mock_http.request_history) == 3
    assert mock_http.request_history[0][0] == 'GET'
```

---

## 9. 향후 확장 방향

### 9.1 추가 가능한 기능

| 기능 | 설명 | 구현 방법 |
|------|------|----------|
| **캐싱** | 학생 정보 캐싱 | `CacheDecorator` 적용 |
| **재시도 로직** | 네트워크 실패 시 자동 재시도 | `RetryDecorator` 적용 |
| **Rate Limiting** | API 호출 제한 | `RateLimiter` 미들웨어 |
| **메트릭 수집** | 성능 모니터링 | `MetricsLogger` 추가 |

### 9.2 새 서비스 추가 방법

```python
# 1. settings.py에 설정 추가
SERVICES['new_service'] = ServiceConfig(
    name='New Service Name',
    auth_url='https://sso.mju.ac.kr/sso/auth?client_id=new_service&...',
    success_domain='new.mju.ac.kr',
    test_url='https://new.mju.ac.kr/main'
)

# 2. 필요 시 새 서비스 클래스 생성
class NewService:
    def __init__(self, http_client: HTTPClient, logger: Logger):
        self.http = http_client
        self.logger = logger
    
    def fetch(self):
        # 구현
        pass

# 3. Facade에 메서드 추가
class MjuUnivAuth:
    def get_new_data(self):
        http_client = self._ensure_login(service='new_service')
        service = NewService(http_client, self._logger)
        return service.fetch()
```

### 9.3 확장 포인트

```python
# 커스텀 HTTP 클라이언트
class CustomHTTPClient(HTTPClient):
    def __init__(self, proxy=None, verify_ssl=True):
        super().__init__()
        self._session.proxies = {'http': proxy, 'https': proxy}
        self._session.verify = verify_ssl

# 커스텀 로거
class FileLogger(Logger):
    def __init__(self, file_path: str):
        self.file = open(file_path, 'a')
    
    def info(self, label, value, indent=2):
        self.file.write(f"{label}: {value}\n")

# 사용
auth = MjuUnivAuth(
    user_id="학번",
    user_pw="비밀번호"
)
auth._http_client = CustomHTTPClient(proxy="http://proxy:8080")
auth._logger = FileLogger("/var/log/mju_auth.log")
```

---

## 결론

이번 리팩토링을 통해 다음을 달성했습니다:

### 일관성 향상
- 네이밍 규칙 통일 (`Service`, `Parser`, `Config`)
- 에러 처리 표준화 (컨텍스트 정보 포함)
- 코드 스타일 일관성

### 단순성 향상
- 각 모듈의 책임 명확화
- 복잡한 로직의 메서드 분리
- 중복 코드 제거 (파싱 로직 통합)

### 유지보수성 향상
- 계층형 아키텍처로 관심사 분리
- 의존성 주입으로 테스트 용이성 확보
- 설정 외부화로 변경 용이성 확보

이 구조는 향후 새로운 기능 추가, 버그 수정, 성능 최적화 시에도 기존 코드에 미치는 영향을 최소화하면서 확장할 수 있도록 설계되었습니다.
