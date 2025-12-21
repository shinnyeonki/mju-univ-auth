# mju-univ-auth

명지대학교 통합 인증(SSO) 및 학생 정보 조회 Python 라이브러리

[![PyPI version](https://badge.fury.io/py/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)
[![Python](https://img.shields.io/pypi/pyversions/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)

<img src="myongji_universiry_auth_logo.png" alt="alt text" width="500">

**GitHub Repository:** [github repo](https://github.com/shinnyeonki/mju-univ-auth)

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
11. [기여 가이드](#11-기여-가이드)

---

## 1. 목적

이 라이브러리는 명지대학교 학생들이 프로그래밍 방식으로 학교 시스템에 접근할 수 있도록 지원합니다.

### 주요 기능

- **명지대 서비스들의 세션 얻기**: 명지대학교 통합 로그인 시스템을 통한 인증 및 세션 획득
- **MSI 서비스 학생 기본 정보 조회**: 기본 정보 조회(학과, 학년, 최근 접속 시간, 최근 접속 IP)
- **MSI 서비스 학적변동내역 조회**: 학적 변동 이력 조회 (학번, 이름, 학적상태, 이수학기, 학과, 누적 휴학학기, 변동내역 리스트)
- **MSI 서비스 학생카드 조회**: 학생카드 정보 조회 (학번, 이름, 학년, 학적상태, 학부(과), 상담교수, 학생설계전공지도교수, 증명사진, 영문 성명, 전화번호, 휴대폰, 이메일, 현거주지 주소등)

---
## 2. 설치 및 테스트

```bash
pip install mju_univ_auth
```

```bash
python -m mju_univ_auth
```
---

## 3. 지원 서비스

`login()` 메서드의 `service` 파라미터로 다양한 서비스에 로그인할 수 있습니다. 각 서비스는 고유한 단축 문자열(코드명)을 사용하여 지정합니다:

| 서비스 | 코드명 | 설명 | 동작 여부 | 관련 클래스 |
|--------|--------|------|--------|--------|
| [명지대 통합 포털](https://portal.mju.ac.kr/) | `"main"` | 기본 포털 | v | `StandardAuthenticator` |
| [학사행정시스템 (MSI)](https://msi.mju.ac.kr/) | `"msi"` | 학생카드, 성적, 수강신청 등 | v | `StandardAuthenticator` |
| [LMS (LearnUs)](https://lms.mju.ac.kr/) | `"lms"` | 강의 자료, 과제 | v | `StandardAuthenticator` |
| [캡스톤/현장실습](https://myicap.mju.ac.kr/) | `"myicap"` | MyiCAP | v | `StandardAuthenticator` |
| [인턴십 시스템](https://intern.mju.ac.kr/) | `"intern"` | 인턴십 관리 | v | `StandardAuthenticator` |
| [IPP (산업연계)](https://ipp.mju.ac.kr/) | `"ipp"` | 산업연계 프로그램 | v | `StandardAuthenticator` |
| [U-CHECK](https://ucheck.mju.ac.kr/) | `"ucheck"` | 출석 확인 | v | `StandardAuthenticator` |
| [Libary](https://lib.mju.ac.kr/) | `"lib"` | 도서관 | x | 구현중 |


```python
# 예: LMS 로그인 후 세션 획득
result = MjuUnivAuth("학번", "비밀번호").login("lms").get_session()
# 예: MSI 로그인후 기본 정보 파싱 ( sso login (0.8s) + msi main page (0.3s) = 1.1s )
result = MjuUnivAuth("학번", "비밀번호").login("msi").get_student_basicinfo()
# 예: MSI 로그인후 학생카드 파싱 ( sso login (0.8s) + msi student card page (0.4s) = 1.2s )
result = MjuUnivAuth("학번", "비밀번호").login("msi").get_student_card()
# 예: MSI 로그인후 학적 변경 파싱 ( sso login (0.8s) + msi student changelog page (0.8s) = 1.6s )
result = MjuUnivAuth("학번", "비밀번호").login("msi").get_student_changelog()
```

## 4. 기본 사용법 (고수준 API)

`MjuUnivAuth` 클래스는 복잡한 내부 로직(세션 관리)을 숨기고 간단한 API를 제공합니다.
```python
result = MjuUnivAuth(user_id="학번", user_pw="비밀번호").login("msi").get_student_card()
```

**중요**: 모든 데이터 조회(`get_student_basicinfo`, `get_student_card`, `get_student_changelog` 등) 전에 반드시 `.login()` 메서드를 호출하여 세션을 초기화해야 합니다.

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
    print(f"이름: {card.student_profile.name_korean}")
    print(f"학번: {card.student_profile.student_id}")
    print(f"학과: {card.student_profile.department}")
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

result = MjuUnivAuth(user_id="학번", user_pw="비밀번호").login("lms").get_session()

if result.success:
    session = result.data  # requests.Session 객체
    # 이 세션으로 LMS 서비스에 추가 요청 가능
    response = session.get("https://lms.mju.ac.kr/...")
```

### 3.3. 상세 로그 출력

디버깅을 위해 상세 로그를 활성화할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.INFO) # INFO or DEBUG

auth = MjuUnivAuth("학번", "비밀번호", verbose=True) # 라이브러리 로그 활성화
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
    NONE = ""
    NETWORK_ERROR = "NETWORK_ERROR" # 명지대 서버(업스트림)와 통신하는 데 실패함
    PARSING_ERROR = "PARSING_ERROR" # 명지대 웹사이트 구조 변경 등으로 서버가 응답을 파싱할 수 없음
    INVALID_CREDENTIALS_ERROR = "INVALID_CREDENTIALS_ERROR" # 아이디/비밀번호 불일치 등 인증 실패
    SESSION_NOT_EXIST_ERROR = "SESSION_NOT_EXIST_ERROR" # 로그인을 하지 않아 세션이 없는 상태. 인증이 필요한 리소스에 접근했으므로 인증을 요구
    SESSION_EXPIRED_ERROR = "SESSION_EXPIRED_ERROR" # 세션이 만료됨. 클라이언트가 재인증(재로그인)을 통해 새로운 세션을 받아야 함
    ALREADY_LOGGED_IN_ERROR = "ALREADY_LOGGED_IN_ERROR" # 이미 로그인된 상태에서 다시 로그인을 시도하는 등 현재 서버의 상태와 충돌되는 요청을 보냄
    SERVICE_NOT_FOUND_ERROR = "SERVICE_NOT_FOUND_ERROR" # 요청 형식은 유효하지만, 내용(존재하지 않는 서비스 이름)을 처리할 수 없음을 의미
    SERVICE_UNKNOWN_ERROR = "SERVICE_UNKNOWN_ERROR" # 알 수 없는 서비스 이름이 요청됨
    INVALID_SERVICE_USAGE_ERROR = "INVALID_SERVICE_USAGE_ERROR" # 현재 로그인된 서비스로는 해당 기능을 사용할 수 없음을 의미
    UNKNOWN_ERROR = "UNKNOWN_ERROR" # 원인을 특정할 수 없는 라이브러리 내부의 일반적인 오류.
```

### 5.3. request_succeeded와 credentials_valid 분리 이유

이 두 필드를 분리하여 다양한 상황을 명확히 구분할 수 있습니다:

| 상황 | request_succeeded | credentials_valid | 의미 |
|------|-------------------|-------------------|------|
| 로그인 성공 | `True` | `True` | 모든 것이 정상 |
| 비밀번호 틀림 | `True` | `False` | 요청은 성공, 인증만 실패 |
| 네트워크 오류 | `False` | `None` | 요청 자체 실패 (인증 여부 알 수 없음) |
| 세션 만료 | `False` | `False` | 이전 인증이 무효화됨 |
| 학생카드 조회 성공 | `True` | `True` | 정상 |
| HTML 파싱 실패 | `False` | `True` | 인증은 유효하나 파싱 오류 |

### 5.4. data 필드
성공 시 `data` 필드에 담기는 데이터 타입은 호출한 메서드에 따라 다릅니다:
- `.get_session()` : `requests.Session` 객체
- `.get_student_basicinfo()` : `StudentBasicInfo` 객체
- `.get_student_card()` : `StudentCard` 객체
- `.get_student_changelog()` : `StudentChangeLog` 객체
#### 5.4.1. 데이터 필드 구조
##### 기본 메인 페이지 정보
`student_basicinfo`

- **dashboard_summary** (대시보드 요약 정보)
	- department (Department / 소속)
	- category (Category / 구분)
	- grade (Grade / 학년)
	- last_access_time (Recent Access Time / 최근 접속 시간)
	- last_access_ip (Recent Access IP / 최근 접속 IP)

#### 학적 변동 내역
`student_changelog`

- **academic_status** (학적 기본 정보)
	- student_id (Student ID / 학번)
	- name (Name / 성명)
	- status (Academic Status / 학적상태)
	- grade (Grade / 학년)
	- completed_semesters (Completed Semesters / 이수학기)
	- department (Department / 학부(과))
- **leave_history** (휴학 누적 현황)
	- cumulative_leave_semesters (Cumulative Leave Semesters / 휴학 누적 학기)
- **change_log_list** (변동 내역 리스트)
	- year (Year / 년도)
	- semester (Semester / 학기)
	- change_type (Change Type / 변동유형)
	- change_date (Change Date / 변동일자)
	- expiry_date (Expiry Date / 만료일자)
	- reason (Reason / 사유)

##### 학생카드
`student-card`

- **student_profile** (학생 상세 정보)
	- student_id (Student ID / 학번)
	- name_korean (Korean Name / 한글성명)
	- grade (Grade / 학년)
	- enrollment_status (Enrollment Status / 학적상태)
	- college_department (College & Department / 학부(과))
	- academic_advisor (Academic Advisor / 상담교수)
	- student_designed_major_advisor (Student Designed Major Advisor / 학생설계전공지도교수)
	- photo_base64 (Photo Base64 / 증명사진)
- **personal_contact** (개인 연락처 정보)
	- english_surname (English Surname / 영문성명-성)
	- english_givenname (English Given Name / 영문성명-이름)
	- phone_number (Phone Number / 전화번호)
	- mobile_number (Mobile Number / 휴대폰)
	- email (E-Mail / 이메일)
	- current_residence_address (Current Residence Address / 현거주지 주소)
		- postal_code (Postal Code / 우편번호)
		- address (Address / 주소)
	- resident_registration_address (Resident Registration Address / 주민등록 주소)
		- postal_code (Postal Code / 우편번호)
		- address (Address / 주소)

### 5.5. 실제 사용 예시

```python
from mju_univ_auth import MjuUnivAuth, ErrorCode

auth = MjuUnivAuth("학번", "비밀번호")
result = auth.login("msi").get_student_card()

# 방법 1: success 프로퍼티로 간단히 확인
if result.success:
    print(result.data.student_profile.name_korean)
else:
    print(f"실패: {result.error_message}")

# 방법 2: 에러 코드별 세분화 처리
if result.success:
    print(result.data.student_profile.name_korean)
elif result.error_code == ErrorCode.INVALID_CREDENTIALS_ERROR:
    print("아이디 또는 비밀번호가 틀렸습니다.")
elif result.error_code == ErrorCode.NETWORK_ERROR:
    print("네트워크 연결을 확인해주세요.")
    # 재시도 로직 구현 가능
elif result.error_code == ErrorCode.SESSION_EXPIRED_ERROR:
    print("세션이 만료되었습니다. 다시 로그인해주세요.")
elif result.error_code == ErrorCode.PARSING_ERROR:
    print("페이지 구조가 변경되었을 수 있습니다.")
else:
    print(f"알 수 없는 오류: {result.error_message}")

# 방법 3: bool 변환 활용 (if result:와 동일)
if not result:
    print("조회 실패")
```

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

Python이 아닌 다른 언어에서 이 라이브러리의 기능을 사용하고 싶다면, 함께 제공되는 `api_server.py`를 실행하여 REST API 서버로 활용할 수 있습니다.

이 API 서버는 [FastAPI](https://fastapi.tiangolo.com/)로 구축되었습니다.

[서버 readme](api/README.md)

[API 서버 코드](api/api_server.py)

[API 서버 대화형 문서](https://mju-univ-auth.shinnk.kro.kr/docs)

[API 서버 명세](https://mju-univ-auth.shinnk.kro.kr/redoc)

---

## 11. 기여 가이드
[기여 가이드](doc/contributing.md)

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 주의사항

- **개인 정보 보호**: 비밀번호를 코드에 직접 작성하지 마세요. 환경 변수나 `.env` 파일을 사용하세요.
- **책임 있는 사용**: 이 라이브러리를 악용하지 마세요.
