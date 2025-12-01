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
├── Authenticator.py         # SSO 인증 로직
├── base_fetcher.py          # Fetcher 기반 클래스 (예외 → Result 변환)
├── student_card_fetcher.py  # 학생카드 조회
├── student_change_log_fetcher.py # 학적변동내역 조회
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
    NETWORK_ERROR = "NETWORK_ERROR"       # 네트워크 연결 실패
    AUTH_FAILED = "AUTH_FAILED"           # 인증 실패 (ID/PW 오류)
    PARSE_ERROR = "PARSE_ERROR"           # HTML 파싱 실패
    SESSION_EXPIRED = "SESSION_EXPIRED"   # 세션 만료
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND" # 지원하지 않는 서비스
    UNKNOWN = "UNKNOWN"                   # 알 수 없는 오류
```

### 3.3. 커스텀 예외 계층

내부 로직에서는 예외를 사용하여 정확한 실패 지점과 원인을 표현합니다.

```python
MjuUnivAuthError (기본)
├── NetworkError          # 네트워크 요청 실패
├── PageParsingError      # HTML 파싱 실패
├── InvalidCredentialsError # 인증 실패
├── SessionExpiredError   # 세션 만료
└── ServiceNotFoundError  # 서비스 미지원
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

사용자가 가장 편하게 사용할 수 있는 객체 입니다.

```python
class MjuUnivAuth:
    """
    복잡한 내부 로직을 숨기고, 단순한 API를 제공
    - 세션 관리 자동화
    - 메서드 체이닝 지원
    - 자동 로그인 (필요 시)
    """
    
    def login(self, service: str = 'msi') -> 'MjuUnivAuth':
        """체이닝을 위해 self 반환"""
        # 내부적으로 Authenticator 사용
        authenticator = Authenticator(user_id, user_pw, verbose)
        result = authenticator.login(service)
        # result 저장 후 self 반환
        return self
    
    def get_student_card(self) -> MjuUnivAuthResult[StudentCard]:
        """자동 로그인 후 학생카드 조회"""
        self._ensure_login(service='msi')  # 필요 시 자동 로그인
        fetcher = StudentCardFetcher(session, user_pw, verbose)
        return fetcher.fetch()
```

#### 사용 예시

```python
# 체이닝
result = MjuUnivAuth("학번", "비번").login().get_student_card()

# 명시적
auth = MjuUnivAuth("학번", "비번")
auth.login("msi")
result = auth.get_student_card()

# 자동 로그인 (login 호출 안 해도 됨)
result = MjuUnivAuth("학번", "비번").get_student_card()
```

### 4.2. Authenticator - SSO 인증 (저수준 API)

로그인을 하여 session 을 얻는 목적입니다 SSO 로그인의 전체 흐름을 처리합니다.

```python
class Authenticator:
    def login(self, service) -> MjuUnivAuthResult[Session]:
        """Public API - 항상 Result 반환"""
        try:
            self._execute_login(session, service)
            return MjuUnivAuthResult(success...)
        except InvalidCredentialsError as e:
            return MjuUnivAuthResult(error...)
    
    def _execute_login(self, session, service):
        """Internal - 예외 발생"""
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
        try:
            data = self._execute()  # 자식 클래스 구현
            return MjuUnivAuthResult(success, data=data)
        except PageParsingError as e:
            return MjuUnivAuthResult(error_code=PARSE_ERROR, ...)
        except NetworkError as e:
            return MjuUnivAuthResult(error_code=NETWORK_ERROR, ...)
        except SessionExpiredError as e:
            return MjuUnivAuthResult(error_code=SESSION_EXPIRED, ...)
        except Exception as e:
            return MjuUnivAuthResult(error_code=UNKNOWN, ...)
    
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
# domain/new_data.py
@dataclass
class NewData:
    field1: str = ""
    
    @classmethod
    def from_parsed_fields(cls, fields):
        return cls(field1=fields.get('필드1'))
```

### 2단계: Fetcher 구현

```python
# new_data_fetcher.py
class NewDataFetcher(BaseFetcher[NewData]):
    def __init__(self, session, verbose=False):
        super().__init__(session)
        self._verbose = verbose
    
    def _execute(self) -> NewData:
        # 페이지 접근, 파싱 로직
        # 실패 시 적절한 예외 raise
        return NewData.from_parsed_fields(fields)
```

### 3단계: Facade에 메서드 추가

```python
# facade.py
class MjuUnivAuth:
    def get_new_data(self) -> MjuUnivAuthResult[NewData]:
        if error := self._ensure_login('msi'):
            return error
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