# mju-univ-auth

명지대학교 통합 인증(SSO) 및 학생 정보 조회 Python 라이브러리

[![PyPI version](https://badge.fury.io/py/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)
[![Python](https://img.shields.io/pypi/pyversions/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)  


<img src="myongji_universiry_auth_logo.png" alt="alt text" width="500">


## 목차

1. [목적](#1-목적)
2. [설치](#2-설치)
3. [기본 사용법 (고수준 API)](#3-기본-사용법-고수준-api)
4. [고급 사용법 (저수준 API)](#4-고급-사용법-저수준-api)
5. [반환값 구조 (MjuUnivAuthResult)](#5-반환값-구조-mjuunivauthresult)
6. [데이터 모델](#6-데이터-모델)
7. [지원 서비스](#7-지원-서비스)
8. [기술적 설명](#8-기술적-설명)
9. [이종 언어를 위한 API 서버](#9-이종-언어를-위한-api-서버)

---

## 1. 목적

이 라이브러리는 명지대학교 학생들이 프로그래밍 방식으로 학교 시스템에 접근할 수 있도록 지원합니다.

### 주요 기능

- **명지대 서비스의 세션 얻기**: 명지대학교 통합 로그인 시스템을 통한 인증 및 세션 획득
- **학생카드 조회**: 학번, 이름, 학과, 학적상태 등 기본 정보 조회
- **학적변동내역 조회**: 학적 변동 이력 조회

---

## 2. 설치

```bash
pip install mju-univ-auth
```

---

### 현 상황
현재 이 라이브러리는
- 명지대 메인 페이지 세션
- 학사행정시스템(MSI)
- LMS
- MyiCAP
- 인턴십 시스템
- IPP
- U-CHECK
명지대 하위 서비스들의 로그인된 세션을 얻을 수 있으며

로그인된 MSI 세션을 통해 학생카드 정보와 학적변동내역을 조회할 수 있습니다.

## 3. 기본 사용법 (고수준 API)

`MjuUnivAuth` 클래스는 복잡한 내부 로직(세션 관리, 자동 로그인 등)을 숨기고 간단한 API를 제공합니다.

### 3.1. 학생카드 정보 조회

```python
from mju_univ_auth import MjuUnivAuth

# 방법 1: 체이닝으로 로그인 후 조회
result = MjuUnivAuth(user_id="학번", user_pw="비밀번호").login("msi").get_student_card()

if result.success:
    card = result.data
    print(f"이름: {card.name_korean}")
    print(f"학번: {card.student_id}")
    print(f"학과: {card.department}")
    print(f"학년: {card.grade}")
    print(f"학적상태: {card.status}")
else:
    print(f"조회 실패: {result.error_message}")

# 방법 2: 자동 로그인 (login 호출 생략 가능)
result = MjuUnivAuth("학번", "비밀번호").get_student_card()
```

### 3.2. 학적변동내역 조회

```python
from mju_univ_auth import MjuUnivAuth

result = MjuUnivAuth(user_id="학번", user_pw="비밀번호").login("msi").get_student_changelog()

if result.success:
    log = result.data
    print(f"학번: {log.student_id}")
    print(f"이름: {log.name}")
    print(f"학적상태: {log.status}")
    print(f"이수학기: {log.completed_semesters}")
```

### 3.3. 세션 획득

다른 서비스(LMS, MyiCAP 등)에 로그인하여 세션만 얻고 싶을 때:

```python
from mju_univ_auth import MjuUnivAuth

auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
result = auth.login("lms").get_session()

if result.success:
    session = result.data  # requests.Session 객체
    # 이 세션으로 LMS 서비스에 추가 요청 가능
    response = session.get("https://lms.mju.ac.kr/...")
```

### 3.4. 상세 로그 출력

디버깅을 위해 상세 로그를 활성화할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.INFO)

auth = MjuUnivAuth("학번", "비밀번호", verbose=True)
result = auth.get_student_card()
```

### 3.5. 환경 변수 사용 (권장)

보안을 위해 환경 변수나 `.env` 파일을 사용하는 것을 권장합니다:

```python
import os
from dotenv import load_dotenv
from mju_univ_auth import MjuUnivAuth

load_dotenv()

auth = MjuUnivAuth(
    user_id=os.getenv('MJU_ID'),
    user_pw=os.getenv('MJU_PW')
)
result = auth.get_student_card()
```

`.env` 파일 예시:
```
MJU_ID=학번
MJU_PW=비밀번호
```

---

## 4. 고급 사용법 (저수준 API)

저수준 API는 개별 컴포넌트를 직접 제어해야 할 때 사용합니다. 스크립트 개발이나 디버깅 시 유용합니다.

### 4.1. Authenticator로 세션 획득

`Authenticator` 클래스는 SSO 로그인만을 담당합니다:

```python
from mju_univ_auth import Authenticator

# 인증 객체 생성
authenticator = Authenticator(
    user_id="학번",
    user_pw="비밀번호",
    verbose=True
)

# 로그인 수행
result = authenticator.login(service='msi')

if result.success:
    session = result.data  # requests.Session 객체
    print("로그인 성공!")
else:
    print(f"로그인 실패: {result.error_code} - {result.error_message}")
```

### 4.2. StudentCardFetcher로 학생카드 조회

`StudentCardFetcher`는 이미 로그인된 세션을 받아 학생카드 정보를 조회합니다:

```python
from mju_univ_auth import Authenticator, StudentCardFetcher

# 1. 먼저 세션 획득
authenticator = Authenticator("학번", "비밀번호")
login_result = authenticator.login('msi')

if not login_result.success:
    print(f"로그인 실패: {login_result.error_message}")
    exit()

session = login_result.data

# 2. Fetcher로 학생카드 조회
fetcher = StudentCardFetcher(
    session=session,
    user_pw="비밀번호",  # 2차 인증에 필요
    verbose=True
)
result = fetcher.fetch()

if result.success:
    card = result.data
    card.print_summary()  # 정보 요약 출력
```

### 4.3. StudentChangeLogFetcher로 학적변동내역 조회

```python
from mju_univ_auth import Authenticator, StudentChangeLogFetcher

# 1. 세션 획득
authenticator = Authenticator("학번", "비밀번호")
login_result = authenticator.login('msi')
session = login_result.data

# 2. 학적변동내역 조회 (2차 인증이 불필요 하므로 비밀번호를 넘길 필요가 없습니다)
fetcher = StudentChangeLogFetcher(
    session=session,
    verbose=True
)
result = fetcher.fetch()

if result.success:
    log = result.data
    log.print_summary()
```

## 5. 반환값 구조 (MjuUnivAuthResult)

모든 API 호출은 예외를 발생시키지 않고 `MjuUnivAuthResult` 객체를 반환합니다.  
이 설계는 서비스 개발 시 오류를 "정상적인 비즈니스 로직"으로 처리할 수 있게 합니다.

### 5.1. MjuUnivAuthResult 구조

```python
@dataclass
class MjuUnivAuthResult(Generic[T]):
    request_succeeded: bool             # 네트워크/파싱 등 요청 성공 여부
    credentials_valid: Optional[bool]   # 인증 성공 여부 (로그인 관련만)
    data: Optional[T]                   # 성공 시 데이터
    error_code: ErrorCode               # 에러 코드
    error_message: str                  # 에러 메시지

    @property
    def success(self) -> bool:
        """통합 성공 판단"""
        ...
```

### 5.2. 주요 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `request_succeeded` | `bool` | 네트워크 요청, HTML 파싱 등 기술적 처리 성공 여부 |
| `credentials_valid` | `Optional[bool]` | 아이디/비밀번호 인증 성공 여부. 데이터 조회 시에는 `True` 또는 `False` |
| `data` | `Optional[T]` | 성공 시 결과 데이터 (`StudentCard`, `StudentChangeLog`, `Session` 등) |
| `error_code` | `ErrorCode` | 에러 종류 구분을 위한 열거형 |
| `error_message` | `str` | 사람이 읽을 수 있는 에러 메시지 |
| `success` | `bool` (property) | 통합 성공 판단. `if result.success:`로 간단히 확인 가능 |

- error_code

```python
class ErrorCode(str, Enum):
    NONE = ""                    # 에러 없음 (성공)
    NETWORK_ERROR = "NETWORK_ERROR"       # 네트워크 연결 실패
    AUTH_FAILED = "AUTH_FAILED"           # 인증 실패 (ID/PW 오류)
    PARSE_ERROR = "PARSE_ERROR"           # HTML 파싱 실패
    SESSION_EXPIRED = "SESSION_EXPIRED"   # 세션 만료
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND" # 지원하지 않는 서비스
    UNKNOWN = "UNKNOWN"                   # 알 수 없는 오류
```

### 5.4. request_succeeded와 credentials_valid 분리 이유

이 두 필드를 분리하여 다양한 상황을 명확히 구분할 수 있습니다:

| 상황 | request_succeeded | credentials_valid | 의미 |
|------|-------------------|-------------------|------|
| 로그인 성공 | `True` | `True` | 모든 것이 정상 |
| 비밀번호 틀림 | `True` | `False` | 요청은 성공, 인증만 실패 |
| 네트워크 오류 | `False` | `None` | 요청 자체 실패 (인증 여부 알 수 없음) |
| 세션 만료 | `False` | `False` | 이전 인증이 무효화됨 |
| 학생카드 조회 성공 | `True` | `True` | 정상 |
| HTML 파싱 실패 | `False` | `True` | 인증은 유효하나 파싱 오류 |

### 5.5. 실제 사용 예시

```python
from mju_univ_auth import MjuUnivAuth, ErrorCode

auth = MjuUnivAuth("학번", "비밀번호")
result = auth.login("msi").get_student_card()

# 방법 1: success 프로퍼티로 간단히 확인
if result.success:
    print(result.data.name_korean)
else:
    print(f"실패: {result.error_message}")

# 방법 2: 에러 코드별 세분화 처리
if result.success:
    print(result.data.name_korean)
elif result.error_code == ErrorCode.AUTH_FAILED:
    print("아이디 또는 비밀번호가 틀렸습니다.")
elif result.error_code == ErrorCode.NETWORK_ERROR:
    print("네트워크 연결을 확인해주세요.")
    # 재시도 로직 구현 가능
elif result.error_code == ErrorCode.SESSION_EXPIRED:
    print("세션이 만료되었습니다. 다시 로그인해주세요.")
elif result.error_code == ErrorCode.PARSE_ERROR:
    print("페이지 구조가 변경되었을 수 있습니다.")
else:
    print(f"알 수 없는 오류: {result.error_message}")

# 방법 3: bool 변환 활용 (if result:와 동일)
if not result:
    print("조회 실패")
```

---

## 6. 데이터 모델

### 6.1. StudentCard (학생카드)

`get_student_card()` 호출 시 `result.data`에 담기는 데이터 클래스입니다.

```python
@dataclass
class StudentCard:
    # 기본 정보
    student_id: str           # 학번
    name_korean: str          # 한글성명
    name_english_first: str   # 영문성명(성)
    name_english_last: str    # 영문성명(이름)
    
    # 학적 정보
    grade: str                # 학년
    status: str               # 학적상태 (재학, 휴학 등)
    department: str           # 학부(과)
    advisor: str              # 상담교수
    design_advisor: str       # 학생설계전공지도교수
    
    # 연락처 정보
    phone: str                # 전화번호
    mobile: str               # 휴대폰
    email: str                # 이메일
    
    # 주소 정보
    current_zip: str          # 현거주지 우편번호
    current_address1: str     # 현거주지 주소1
    current_address2: str     # 현거주지 주소2
    registered_zip: str       # 주민등록 우편번호
    registered_address1: str  # 주민등록 주소1
    registered_address2: str  # 주민등록 주소2
    
    # 기타
    photo_base64: str         # 사진 (Base64 인코딩)
    focus_newsletter: bool    # 명지포커스 수신여부
    
    # 계산된 속성
    @property
    def name_english(self) -> str: ...      # 영문 성명 전체
    @property
    def current_address(self) -> str: ...   # 현거주지 전체 주소
    @property
    def registered_address(self) -> str: ...# 주민등록 전체 주소
    
    # 메서드
    def to_dict(self) -> Dict: ...          # 딕셔너리로 변환
    def print_summary(self) -> None: ...    # 정보 요약 출력
```

### 6.2. StudentChangeLog (학적변동내역)

`get_student_changelog()` 호출 시 `result.data`에 담기는 데이터 클래스입니다.

```python
@dataclass
class StudentChangeLog:
    student_id: str           # 학번
    name: str                 # 성명
    status: str               # 학적상태
    grade: str                # 학년
    completed_semesters: str  # 이수학기
    department: str           # 학부(과)
    
    # 메서드
    def to_dict(self) -> Dict: ...       # 딕셔너리로 변환
    def print_summary(self) -> None: ... # 정보 요약 출력
```

---

## 7. 지원 서비스

`login()` 메서드의 `service` 파라미터로 다양한 서비스에 로그인할 수 있습니다:

| 서비스 | 코드명 | 설명 |
|--------|--------|------|
| 명지대 통합 포털 | `"main"` | 기본 포털 |
| 학사행정시스템 (MSI) | `"msi"` | 학생카드, 성적, 수강신청 등 |
| LMS (LearnUs) | `"lms"` | 강의 자료, 과제 |
| 캡스톤/현장실습 | `"myicap"` | MyiCAP |
| 인턴십 시스템 | `"intern"` | 인턴십 관리 |
| IPP (산업연계) | `"ipp"` | 산업연계 프로그램 |
| U-CHECK | `"ucheck"` | 출석 확인 |

```python
# 예: LMS 로그인 후 세션 획득
result = MjuUnivAuth("학번", "비밀번호").login("lms").get_session()
```

---

## 8. 기술적 설명

2025년 11월 27일부로 명지대학교의 여러 서비스들이 1개의 로그인 방식(서버측 Spring Security 예상)으로 통합되었습니다.

기존 방식의 경우 서비스별로 평문(userId, password), 암호화 방식 등 여러 방식을 사용했지만, 현재는 모든 로그인이 **RSA+AES 하이브리드 암호화 구조**로 비밀번호를 암호화하여 전송됩니다 (HTTPS와는 무관한 중복 암호화).

과거 전송 서버측 API가 현재(2025/11/29) 아직 살아있지만 언제 막힐지 몰라 해당 라이브러리를 만들었습니다.

```bash
# 구 API (현재 사용하지 않지만 동작하는 예시)
curl --location --request POST 'https://sso1.mju.ac.kr/mju/userCheck.do' \
--header 'id: USERID' \
--header 'passwd: PASSWORD'
```

[기술적 설명 상세](doc/sso_login_process.md)

---

## 9. 이종 언어를 위한 API 서버

Python이 아닌 다른 언어에서 사용하려면 API 서버를 활용하세요.

[서버 문서](api/README.md)

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 주의사항

- **개인 정보 보호**: 비밀번호를 코드에 직접 작성하지 마세요. 환경 변수나 `.env` 파일을 사용하세요.
- **책임 있는 사용**: 이 라이브러리를 악용하지 마세요. 개인 학사 관리 목적으로만 사용하세요.
