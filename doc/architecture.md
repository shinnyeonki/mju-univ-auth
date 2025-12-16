# mju-univ-auth 아키텍처 문서

## 1. 개요

`mju-univ-auth`는 명지대학교 SSO 인증 및 학생 정보 조회를 위한 Python 라이브러리입니다.

이 문서에서는 현재 코드베이스의 구조와 각 설계 결정의 배경을 상세히 설명합니다.

## 2. 디렉토리 구조

```
mju_univ_auth/
├── __init__.py              # Public API 정의 및 모듈 export
├── __main__.py              # CLI 진입점
│
├── facade.py                # MjuUnivAuth - 사용자 친화적 고수준 API
│
├── authenticator/           # 인증 관련 로직
│   ├── base_authenticator.py  # Authenticator 기반 클래스
│   └── standard_authenticator.py # 표준 SSO 인증 로직
│
├── fetcher/                 # 데이터 조회 관련 로직
│   ├── base_fetcher.py      # Fetcher 기반 클래스
│   ├── student_card_fetcher.py # 학생카드 조회
│   └── student_change_log_fetcher.py # 학적변동내역 조회
│
├── results.py               # MjuUnivAuthResult - 통합 결과 객체
├── exceptions.py            # 커스텀 예외 클래스들
├── config.py                # 서비스 URL, 타임아웃 설정
│
├── domain/                  # 순수 데이터 모델
│   ├── student_card.py      # StudentCard 데이터 클래스
│   └── student_changelog.py # StudentChangeLog 데이터 클래스
│
├── infrastructure/          # 인프라 계층
│   ├── parser.py            # HTMLParser - HTML 파싱 유틸리티
│   └── crypto.py            # RSA/AES 암호화 유틸리티
│
└── utils/                   # 유틸리티
    └── __init__.py          # mask_sensitive 등
```

## 3. 핵심 설계 원칙

### 3.1. 이중 결과 처리 (Result + Exception)

이 라이브러리의 가장 핵심적인 설계 결정입니다.

#### 문제 인식

라이브러리 사용자는 크게 두 부류로 나뉩니다:

1. **서비스 개발자**: 로그인 실패, 네트워크 오류 등을 "정상적인 비즈니스 로직"으로 처리해야 함
2. **스크립트 개발자**: 빠르게 작성하고, 오류는 예외로 터트려 즉시 확인하고 싶음

```python
# 서비스 개발자가 원하는 방식
result = auth.login()
if not result.success:
    if result.error_code == ErrorCode.AUTH_FAILED:
        return {"error": "아이디 또는 비밀번호가 틀렸습니다"}
    elif result.error_code == ErrorCode.NETWORK_ERROR:
        return {"error": "서버 연결 실패"}

# 스크립트 개발자가 원하는 방식
session = authenticator._execute_login(session, 'msi')  # 실패하면 예외!
```

#### 해결책: 계층 분리

```
┌─────────────────────────────────────────────────────────────┐
│  Public API Layer (facade.py, Authenticator.login)          │
│  → 항상 MjuUnivAuthResult 반환                               │
│  → 예외를 catch하여 Result로 변환                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Internal Layer (_execute_login, _execute, etc.)            │
│  → 실패 시 커스텀 예외 raise                                  │
│  → 개발/디버깅 시 직접 호출 가능                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2. MjuUnivAuthResult - 통합 결과 객체

```python
@dataclass
class MjuUnivAuthResult(Generic[T]):
    request_succeeded: bool             # 네트워크/파싱 성공 여부
    credentials_valid: Optional[bool]   # 인증 성공 여부 (로그인 관련만)
    data: Optional[T]                   # 성공 시 데이터
    error_code: ErrorCode               # 에러 코드
    error_message: str                  # 에러 메시지

    @property
    def success(self) -> bool:
        """통합 성공 판단"""
        if self.credentials_valid is None:
            return self.request_succeeded
        return self.request_succeeded and self.credentials_valid is True
```

#### 왜 `request_succeeded`와 `credentials_valid`를 분리했는가?

| 상황                    | request_succeeded | credentials_valid | 의미                              |
| --------------------- | ----------------- | ----------------- | ------------------------------- |
| 로그인 성공                | True              | True              | 모든 것이 정상                        |
| 비밀번호 틀림               | True              | False             | 요청은 성공, 인증만 실패                  |
| 네트워크 오류               | False             | None              | 요청 자체 실패 (인증 여부 알 수 없음)         |
| 세션 만료 (데이터 조회 중)      | False             | False             | 이전 인증이 무효화됨                     |
| 학생카드 조회 성공            | True              | True              | 정상 (이미 로그인됨)                    |
| 학생카드 페이지 파싱 실패        | False             | True              | 인증은 유효하나 파싱 오류                  |

이 분리를 통해:
- **비밀번호 틀림과 네트워크 오류를 명확히 구분** 가능
- **재시도 로직 구현이 쉬움** (네트워크 오류만 재시도)
- **사용자에게 정확한 에러 메시지** 전달 가능

#### ErrorCode Enum

```python
class ErrorCode(str, Enum):
    NONE = ""
    NETWORK_ERROR = "NETWORK_ERROR"
    AUTH_FAILED = "AUTH_FAILED"
    PARSE_ERROR = "PARSE_ERROR"
    SESSION_NOT_EXIST = "SESSION_NOT_EXIST"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SERVICE_INVALID = "SERVICE_INVALID"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    ALREADY_LOGGED_IN = "ALREADY_LOGGED_IN"
    UNKNOWN = "UNKNOWN"
```

### 3.3. 커스텀 예외 계층

내부 로직에서는 예외를 사용하여 정확한 실패 지점과 원인을 표현합니다.

```python
MjuUnivAuthError (기본)
├── NetworkError
├── ParsingError
├── InvalidCredentialsError
├── SessionExpiredError
├── SessionNotExistError
├── AlreadyLoggedInError
├── ServiceNotFoundError
└── InvalidServiceUsageError
```

#### 예외에 Context 정보 포함

```python
class NetworkError(MjuUnivAuthError):
    def __init__(self, message, url=None, status_code=None, original_error=None, **context):
        self.url = url
        self.status_code = status_code
        self.original_error = original_error
        # ...
```

디버깅 시 `raise NetworkError("접속 실패", url="https://...", status_code=500)`처럼 
풍부한 정보를 담을 수 있습니다.

## 4. 계층별 상세 설명

### 4.1. Facade Layer - `MjuUnivAuth` (고수준 API)

사용자가 가장 편하게 사용할 수 있는 메인 클래스입니다. 복잡한 내부 로직(인증, 세션 관리, Fetcher 인스턴스화 등)을 캡슐화하고 간단한 API를 제공합니다.

**"하나의 인스턴스는 하나의 성공적인 세션만 책임진다"** 원칙을 따릅니다. `login()` 호출이 성공하면 세션이 인스턴스 내에 저장되고, 실패하면 이후 모든 데이터 조회 메서드는 해당 로그인 실패 `Result`를 즉시 반환합니다.

```python
class MjuUnivAuth:
    """
    - 세션 관리 자동화
    - 메서드 체이닝 지원
    - 명시적 로그인 필요
    """
    
    def __init__(self, user_id, user_pw, verbose=False):
        # ...
        self._session: Optional[requests.Session] = None
        self._login_failed: bool = False
        self._login_error: Optional[MjuUnivAuthResult] = None

    def login(self, service: str = 'msi') -> 'MjuUnivAuth':
        """
        로그인 성공 시 세션을 내부에 저장하고, 체이닝을 위해 self 반환.
        실패 시 에러 상태를 저장.
        """
        authenticator = StandardAuthenticator(...)
        result = authenticator.login(service)
        
        if result.success:
            self._session = result.data
            # ...
        else:
            self._login_failed = True
            self._login_error = result
        return self
    
    def get_student_card(self) -> MjuUnivAuthResult[StudentCard]:
        """학생카드 조회"""
        # 로그인 실패했거나, 세션이 없으면 에러 반환
        if self._login_failed:
            return self._login_error
        if self._session is None:
            return MjuUnivAuthResult(error_code=ErrorCode.SESSION_NOT_EXIST, ...)
        
        fetcher = StudentCardFetcher(self._session, ...)
        return fetcher.fetch()
```

#### 사용 예시

```python
# 1. 인스턴스 생성 및 로그인
auth = MjuUnivAuth("학번", "비번")
login_result = auth.login("msi") # login()은 self를 반환

# 2. 로그인 성공 여부 확인 (선택 사항)
if not auth.is_logged_in():
    # auth.get_session()을 통해 구체적인 로그인 실패 원인 확인 가능
    print(f"로그인 실패: {auth.get_session().error_message}")
    return

# 3. 정보 조회
card_result = auth.get_student_card()
if card_result.success:
    print(card_result.data.name_korean)

# 체이닝을 이용한 한 줄 호출
card_result = MjuUnivAuth("학번", "비번").login("msi").get_student_card()
```

### 4.2. Authenticator - SSO 인증 (저수준 API)

`authenticator` 패키지는 로그인을 수행하여 `requests.Session`을 얻는 것을 목적으로 합니다. SSO 로그인의 전체 흐름을 처리하며, 역할에 따라 두 개의 클래스로 분리되었습니다.

- **`BaseAuthenticator`**: 인증 로직의 뼈대를 정의하는 추상 기반 클래스입니다. `login` 메서드는 예외를 `MjuUnivAuthResult`로 변환하는 상위 수준 API 역할을 합니다.
- **`StandardAuthenticator`**: `BaseAuthenticator`를 상속받아 실제 명지대학교 표준 SSO 인증 로직을 구현합니다. 내부 `_execute_login` 메서드는 실패 시 예외를 발생시키는 저수준 API 역할을 합니다.

```python
# base_authenticator.py
class BaseAuthenticator:
    def login(self, service) -> MjuUnivAuthResult[Session]:
        """Public API - 항상 Result 반환"""
        try:
            # 자식 클래스의 _execute_login 호출
            self._execute_login(session, service)
            return MjuUnivAuthResult(success...)
        except InvalidCredentialsError as e:
            return MjuUnivAuthResult(error...)
        # ... other exceptions

    def _execute_login(self, session, service):
        """Internal - 자식 클래스에서 구현, 예외 발생"""
        raise NotImplementedError

# standard_authenticator.py
class StandardAuthenticator(BaseAuthenticator):
    def _execute_login(self, session, service):
        """Internal - 실제 로직 구현, 예외 발생"""
        if self.is_session_valid(service):
            raise AlreadyLoggedInError(...)
            
        self._fetch_login_page(...)      # 1. 페이지 접속
        encrypted = self._prepare_encrypted_data()  # 2. 암호화
        response = self._submit_login(...)  # 3. 로그인 요청
        response = self._handle_redirects(...)  # 4. 리다이렉트 처리
        self._validate_login_result(...)  # 5. 결과 검증
```



### 4.3. BaseFetcher - 데이터 조회 기반 클래스(저수준 API)

> 모든 fetcher 는 로그인된 세션을 기반으로 원하는 정보를 파싱합니다

**예외를 MjuUnivAuthResult로 변환**하는 핵심 로직을 담당합니다.

```python
class BaseFetcher(Generic[T]):
    def fetch(self) -> MjuUnivAuthResult[T]:
        """Template Method Pattern"""
        if self.session is None:
            # 세션이 없는 경우 즉시 에러 Result 반환
            try:
                raise SessionNotExistError()
            except SessionNotExistError as e:
                return MjuUnivAuthResult(error_code=ErrorCode.SESSION_NOT_EXIST, ...)

        try:
            data = self._execute()  # 자식 클래스 구현
            return MjuUnivAuthResult(success, data=data)
        except ParsingError as e:
            return MjuUnivAuthResult(error_code=ErrorCode.PARSE_ERROR, ...)
        except NetworkError as e:
            return MjuUnivAuthResult(error_code=ErrorCode.NETWORK_ERROR, ...)
        except SessionExpiredError as e:
            return MjuUnivAuthResult(error_code=ErrorCode.SESSION_EXPIRED, ...)
        except Exception as e:
            return MjuUnivAuthResult(error_code=ErrorCode.UNKNOWN, ...)
    
    def _execute(self) -> T:
        """자식 클래스에서 구현 - 예외를 raise"""
        raise NotImplementedError
```

#### 장점

- 새로운 Fetcher 추가 시 BaseFetcher 를 상속받고  `_execute()`만 구현하면 됨
- 예외 처리 로직 중복 제거
- 일관된 Result 반환 보장

### 4.4. Domain Layer - 순수 데이터 모델

네트워크 로직 없이 **순수 데이터**만 담습니다.

```python
@dataclass
class StudentCard:
    student_id: str = ""
    name_korean: str = ""
    # ... 필드들
    
    @property
    def name_english(self) -> str:
        """계산된 속성"""
        return f"{self.name_english_first} {self.name_english_last}"
    
    def to_dict(self) -> Dict:
        """직렬화 지원"""
        return {...}
    
    @classmethod
    def from_parsed_fields(cls, fields: Dict) -> 'StudentCard':
        """팩토리 메서드"""
        return cls(
            student_id=fields.get('학번', ''),
            ...
        )
```

### 4.5. Infrastructure Layer

#### HTMLParser - 파싱 전략

정규표현식 → BeautifulSoup 폴백 전략을 사용합니다.

```python
class HTMLParser:
    @classmethod
    def extract_login_page_data(cls, html):
        # 1차: 정규표현식 (빠름)
        match = re.search(r'...', html)
        if match:
            return result
        
        # 2차: BeautifulSoup (정확함, 느림)
        soup = BeautifulSoup(html, 'lxml')
        return soup.find(...)
```

#### Crypto - 암호화

SSO가 요구하는 RSA+AES 하이브리드 암호화를 구현합니다.

```python
# 1. 세션키 생성 (PBKDF2로 AES 키 파생)
key_info = generate_session_key(32)

# 2. RSA로 세션키 암호화 (서버 공개키 사용)
encsymka = encrypt_with_rsa(keyStr + timestamp, public_key)

# 3. AES로 비밀번호 암호화
pw_enc = encrypt_with_aes(password, key_info)
```

## 5. 설정 관리 (config.py)

모든 URL, 타임아웃 등을 중앙에서 관리합니다.

```python
SERVICES: Dict[str, ServiceConfig] = {
    'msi': ServiceConfig(
        name='MSI (학사행정시스템)',
        auth_url='https://sso.mju.ac.kr/sso/auth?client_id=msi&...',
        final_url='https://msi.mju.ac.kr/servlet/security/...',
    ),
    'lms': ServiceConfig(...),
    # ...
}

class MSIUrls:
    HOME = "https://msi.mju.ac.kr/..."
    STUDENT_CARD = "https://msi.mju.ac.kr/servlet/..."
    # ...
```

## 6. 로깅 전략

표준 `logging` 모듈을 사용하며, `verbose` 파라미터로 제어합니다.

```python
import logging
logger = logging.getLogger(__name__)

class Authenticator:
    def __init__(self, user_id, user_pw, verbose=False):
        self._verbose = verbose
    
    def _fetch_login_page(self, url):
        if self._verbose:
            logger.info("[Step 1] 로그인 페이지 접속")
            logger.debug(f"GET {url}")
```

사용자가 로그를 보려면:

```python
import logging
logging.basicConfig(level=logging.INFO)

auth = MjuUnivAuth("학번", "비번", verbose=True)
```

## 7. 확장 가이드

새로운 데이터 조회 기능을 추가하려면:

### 1단계: Domain 모델 생성

```python
# mju_univ_auth/domain/new_data.py
@dataclass
class NewData:
    field1: str = ""
    
    @classmethod
    def from_parsed_fields(cls, fields):
        return cls(field1=fields.get('필드1'))
```

### 2단계: Fetcher 구현

`fetcher` 디렉토리 내에 새로운 fetcher 파일을 생성합니다.

```python
# mju_univ_auth/fetcher/new_data_fetcher.py
from .base_fetcher import BaseFetcher
from ..domain.new_data import NewData

class NewDataFetcher(BaseFetcher[NewData]):
    def __init__(self, session, verbose=False):
        super().__init__(session)
        self._verbose = verbose
    
    def _execute(self) -> NewData:
        # 페이지 접근, 파싱 로직
        # response = self.session.get(...)
        # fields = HTMLParser.parse_new_data(response.text)
        # 실패 시 적절한 예외 raise
        # if not fields:
        #     raise ParsingError("새로운 데이터 파싱 실패")
        return NewData.from_parsed_fields(fields)
```

### 3단계: Facade에 메서드 추가

```python
# mju_univ_auth/facade.py
from .fetcher.new_data_fetcher import NewDataFetcher
from .domain.new_data import NewData

class MjuUnivAuth:
    # ... 기존 코드 ...

    def get_new_data(self) -> MjuUnivAuthResult[NewData]:
        # 로그인 실패 시 저장된 에러 반환
        if self._login_failed:
            return self._login_error
        # 세션이 없는 경우 에러 반환
        if self._session is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.SESSION_NOT_EXIST,
                error_message="세션이 없습니다. 먼저 login()을 호출해주세요."
            )
        
        # 특정 서비스 로그인이 필요한 경우, 서비스 체크
        # if self._service != 'msi':
        #     return MjuUnivAuthResult(error_code=ErrorCode.SERVICE_INVALID, ...)

        fetcher = NewDataFetcher(self._session, self._verbose)
        return fetcher.fetch()
```

## 8. 요약

| 설계 결정               | 이유                                    |
| ------------------- | ------------------------------------- |
| Result + Exception 이중 구조 | 서비스 개발자와 스크립트 개발자 모두 지원 |
| request/credentials 분리 | 네트워크 오류와 인증 실패 명확히 구분 |
| BaseFetcher 템플릿      | 예외→Result 변환 로직 중복 제거          |
| Facade 패턴           | 복잡한 내부 로직 캡슐화, 간단한 API 제공   |
| 정규식+BS 폴백 파싱       | 성능과 정확성 균형                       |
| verbose 파라미터       | 표준 logging 활용, 선택적 디버그 출력    |
| 중앙 집중 설정 (config) | URL 변경 시 한 곳만 수정                 |