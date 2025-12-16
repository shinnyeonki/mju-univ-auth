# mju-univ-auth

명지대학교 통합 인증(SSO) 및 학생 정보 조회 Python 라이브러리

[![PyPI version](https://badge.fury.io/py/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)
[![Python](https://img.shields.io/pypi/pyversions/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)  


<img src="myongji_universiry_auth_logo.png" alt="alt text" width="500">


## 목차

1. [목적](#1-목적)
2. [설치](#2-설치)
3. [지원 서비스](#3-지원-서비스)
4. [기본 사용법 (고수준 API)](#4-기본-사용법-고수준-api)
5. [고급 사용법 (저수준 API)](doc/raw_usage.md)
6. [반환값 구조 (MjuUnivAuthResult)](#6-반환값-구조-mjuunivauthresult)
7. [성공 시 데이터 필드 내용](#7-성공-시-데이터-필드-내용)
8. [동시성 사용 팁](doc/concurrent_usage.md)
9. [기술적 설명](#9-기술적-설명)
10. [이종 언어를 위한 API 서버](#10-이종-언어를-위한-api-서버)

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

## 3. 지원 서비스

`login()` 메서드의 `service` 파라미터로 다양한 서비스에 로그인할 수 있습니다. 각 서비스는 고유한 단축 문자열(코드명)을 사용하여 지정합니다:

| 서비스 | 코드명 | 설명 |
|--------|--------|------|
| 명지대 통합 포털 | `"main"` | 기본 포털 | v | `StandardAuthenticator` |
| 학사행정시스템 (MSI) | `"msi"` | 학생카드, 성적, 수강신청 등 | v | `StandardAuthenticator` |
| LMS (LearnUs) | `"lms"` | 강의 자료, 과제 | v | `StandardAuthenticator` |
| 캡스톤/현장실습 | `"myicap"` | MyiCAP | v | `StandardAuthenticator` |
| 인턴십 시스템 | `"intern"` | 인턴십 관리 | v | `StandardAuthenticator` |
| IPP (산업연계) | `"ipp"` | 산업연계 프로그램 | v | `StandardAuthenticator` |
| U-CHECK | `"ucheck"` | 출석 확인 | v | `StandardAuthenticator` |
| Libary | `"lib"` | 도서관 | x | 구현중 |


```python
# 예: LMS 로그인 후 세션 획득
result = MjuUnivAuth("학번", "비밀번호").login("lms").get_session()
```


## 4. 기본 사용법 (고수준 API)

`MjuUnivAuth` 클래스는 복잡한 내부 로직(세션 관리)을 숨기고 간단한 API를 제공합니다.
```python
result = MjuUnivAuth(user_id="학번", user_pw="비밀번호").login("msi").get_student_card()
```

**중요**: 모든 데이터 조회(`get_student_card`, `get_student_changelog` 등) 전에 반드시 `.login()` 메서드를 호출하여 세션을 초기화해야 합니다.

### 3.1. 데이터 조회 (학생카드, 학적변동내역)

`.login()`을 호출하여 인증을 수행한 뒤, 이어서 학생 정보 조회 메서드를 체이닝(chaining)할 수 있습니다.

```python
from mju_univ_auth import MjuUnivAuth

# 1. MjuUnivAuth 인스턴스 생성
auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")

# 2. 'msi' 서비스로 로그인 후 학생카드 조회
card_result = auth.login("msi").get_student_card()

if card_result.success:
    card = card_result.data
    print(f"이름: {card.name_korean}")
    print(f"학번: {card.student_id}")
    print(f"학과: {card.department}")
else:
    print(f"학생카드 조회 실패: {card_result.error_message}")

# 3. 이미 로그인된 세션을 사용하여 학적변동내역 조회
# 별도로 login()을 다시 호출할 필요가 없습니다.
changelog_result = auth.get_student_changelog()

if changelog_result.success:
    log = changelog_result.data
    print(f"학적상태: {log.status}")
    print(f"이수학기: {log.completed_semesters}")
else:
    print(f"학적변동내역 조회 실패: {changelog_result.error_message}")
```

### 3.2. 세션 획득

다른 서비스(LMS, MyiCAP 등)에 로그인하여 세션만 얻고 싶을 때 사용법은 동일합니다.

```python
from mju_univ_auth import MjuUnivAuth

auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
result = auth.login("lms").get_session()

if result.success:
    session = result.data  # requests.Session 객체
    # 이 세션으로 LMS 서비스에 추가 요청 가능
    response = session.get("https://lms.mju.ac.kr/...")
```

### 3.3. 상세 로그 출력

디버깅을 위해 상세 로그를 활성화할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.INFO)

auth = MjuUnivAuth("학번", "비밀번호", verbose=True)
result = auth.login("msi").get_student_card()
```

### 3.4. 환경 변수 사용 (권장)

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
result = auth.login("msi").get_student_card()
```

`.env` 파일 예시:
```
MJU_ID=학번
MJU_PW=비밀번호
```

---

## 5. 고급 사용법 (저수준 API)

[고급 사용법 상세](doc/raw_usage.md)

## 6. 반환값 구조 (MjuUnivAuthResult)

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

## 7. 성공 시 데이터 필드 내용

성공 시 `result.data` 필드에 담기는 데이터 타입은 다음과 같습니다:

- **StudentCard**: 학생카드 정보 (학번, 이름, 학과 등)
- **StudentChangeLog**: 학적변동내역 (학적상태, 이수학기 등)
- **Session**: requests.Session 객체 (세션 획득 시)

---

## 8. 동시성 사용 팁

[동시성 사용 팁 상세](doc/concurrent_usage.md)

## 9. 기술적 설명

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

## 10. 이종 언어를 위한 API 서버

Python이 아닌 다른 언어에서 사용하려면 API 서버를 활용하세요.

[서버 문서](api/README.md)

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 주의사항

- **개인 정보 보호**: 비밀번호를 코드에 직접 작성하지 마세요. 환경 변수나 `.env` 파일을 사용하세요.
- **책임 있는 사용**: 이 라이브러리를 악용하지 마세요. 개인 학사 관리 목적으로만 사용하세요.
