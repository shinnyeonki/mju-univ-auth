# `mju_univ_auth` 모듈 에러 상세 문서

이 문서는 `mju_univ_auth` 라이브러리 사용 중 발생할 수 있는 모든 커스텀 예외(Exception)에 대해 상세히 설명합니다. 각 에러가 어떤 상황에서, 어떤 조건으로 발생하는지, 그리고 가능한 해결 방안은 무엇인지 안내합니다.

## 1. 에러 클래스 계층 구조

`mju_univ_auth`의 모든 커스텀 에러는 `MjuUnivAuthError`를 상속받습니다.

```
MjuUnivAuthError
├── NetworkError
├── ParsingError
├── InvalidCredentialsError
├── SessionExpiredError
├── SessionNotExistError
├── AlreadyLoggedInError
├── ServiceNotFoundError
└── InvalidServiceUsageError
```

## 2. `ErrorCode`와 HTTP 상태 코드 매핑

라이브러리 내부에서 발생하는 예외는 `MjuUnivAuthResult` 객체의 `error_code`로 변환됩니다. API 서버 등에서 이 라이브러리를 사용하는 경우, 다음 표를 참고하여 `error_code`를 적절한 HTTP 상태 코드로 변환할 수 있습니다.

| 라이브러리 예외 클래스 | `ErrorCode` Enum | HTTP 상태 코드 | 설명 |
| :--- | :--- | :--- | :--- |
| `InvalidCredentialsError` | `INVALID_CREDENTIALS_ERROR` | **401 Unauthorized** | 아이디/비밀번호 불일치 등 인증 실패. 클라이언트가 재인증을 시도해야 함. |
| `SessionNotExistError` | `SESSION_NOT_EXIST_ERROR` | **401 Unauthorized** | 로그인을 하지 않아 세션이 없는 상태. 인증이 필요한 리소스에 접근했으므로 인증을 요구. |
| `SessionExpiredError` | `SESSION_EXPIRED_ERROR` | **401 Unauthorized** | 세션이 만료됨. 클라이언트가 재인증(재로그인)을 통해 새로운 세션을 받아야 함. |
| `InvalidServiceUsageError`| `INVALID_SERVICE_USAGE_ERROR` | **403 Forbidden** | 인증은 되었으나, 현재 로그인된 서비스로는 해당 기능을 사용할 권한이 없음을 의미. |
| `AlreadyLoggedInError` | `ALREADY_LOGGED_IN_ERROR` | **409 Conflict** | 이미 로그인된 상태에서 다시 로그인을 시도하는 등 현재 서버의 상태와 충돌되는 요청을 보냄. |
| `ServiceNotFoundError` | `SERVICE_NOT_FOUND_ERROR` | **422 Unprocessable Entity** | 요청 형식은 유효하지만, 내용(존재하지 않는 서비스 이름)을 처리할 수 없음을 의미. |
| `MjuUnivAuthError` | `UNKNOWN_ERROR` | **500 Internal Server Error** | 원인을 특정할 수 없는 라이브러리 내부의 일반적인 오류. 서버 측의 예외 상황. |
| `ParsingError` | `PARSING_ERROR` | **500 Internal Server Error** | 명지대 웹사이트 구조 변경 등으로 서버가 응답을 파싱할 수 없음. 서버 로직 수정이 필요한 문제. |
| `NetworkError` | `NETWORK_ERROR` | **502 Bad Gateway** | API 서버가 명지대 서버(업스트림)와 통신하는 데 실패함. 게이트웨이 역할을 하는 API 서버에 적합한 코드. |

---

## 3. 최상위 및 일반 에러

### `MjuUnivAuthError`

-   **설명**: `mju_univ_auth` 라이브러리에서 발생하는 모든 문제에 대한 최상위 기본 예외 클래스입니다. 보통 더 구체적인 하위 에러 클래스로 발생하지만, 특정할 수 없는 문제가 생겼을 때 직접 발생할 수 있습니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/authenticator/standard_authenticator.py`
    -   **함수**: `_validate_login_result()`
    -   **조건**: SSO 로그인 성공/실패 여부를 명확히 판단할 수 없는 예외적인 상태일 때 발생합니다. (예: 서버 응답에 에러 메시지도 없고, 성공적인 리다이렉션도 아닌 경우)
-   **해결 방안**:
    -   `verbose=True` 옵션을 켜서 상세 로그를 확인하고, 명지대학교 웹 서비스의 동작이 변경되었는지 점검해야 합니다.

---

## 3. 네트워크 관련 에러

### `NetworkError`

-   **설명**: 명지대학교 서버와의 HTTP 통신 과정에서 문제가 발생했을 때 발생하는 예외입니다. 주로 `requests.RequestException`을 감싸서 발생시킵니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/authenticator/standard_authenticator.py`, `mju_univ_auth/fetcher/student_card_fetcher.py`, `mju_univ_auth/fetcher/student_change_log_fetcher.py`
    -   **조건**:
        1.  **SSO 로그인 페이지 접속 실패**: (`standard_authenticator.py`, `_fetch_login_page`)
            -   `requests.get()` 호출 중 DNS 조회 실패, 연결 거부, 타임아웃 등이 발생할 때.
        2.  **암호화된 로그인 정보 전송 실패**: (`standard_authenticator.py`, `_submit_login`)
            -   `requests.post()`로 암호화된 자격 증명을 전송하는 과정에서 네트워크 문제가 발생할 때.
        3.  **리다이렉트 처리 실패**: (`standard_authenticator.py`, `_handle_redirects`)
            -   로그인 과정에서 JavaScript 리다이렉션 또는 폼 제출을 처리하는 동안 네트워크 문제가 발생할 때.
        4.  **CSRF 토큰 획득 실패**: (`student_card_fetcher.py` 및 `student_change_log_fetcher.py`, `_get_csrf_token`)
            -   MSI 메인 페이지(`MySecurityStart`)에 접속하여 CSRF 토큰을 가져오는 과정에서 네트워크 문제가 발생할 때.
        5.  **학생카드/학적변동내역 페이지 접근 실패**: (`student_card_fetcher.py`, `_access_student_card_page` / `student_change_log_fetcher.py`, `_access_changelog_page`)
            -   로그인 후, 각 정보 페이지에 `POST` 요청을 보내는 과정에서 네트워크 문제가 발생할 때.
        6.  **2차 비밀번호 인증 실패**: (`student_card_fetcher.py`, `_submit_password`)
            -   학생카드 조회 시, 2차 비밀번호를 전송하는 과정에서 네트워크 문제가 발생할 때.
-   **해결 방안**:
    -   인터넷 연결 상태를 확인합니다.
    -   방화벽이나 프록시가 명지대학교 서버(`sso.mju.ac.kr`, `msi.mju.ac.kr`)로의 연결을 차단하고 있는지 확인합니다.
    -   명지대학교 서버가 점검 중이거나 일시적으로 다운되었을 수 있으니, 잠시 후 다시 시도합니다.

---

## 4. 페이지 파싱 관련 에러

### `ParsingError`

-   **설명**: 서버로부터 받은 HTML 응답을 분석(파싱)하여 필요한 정보를 추출하는 데 실패했을 때 발생하는 예외입니다. 이는 명지대학교 웹 페이지의 구조가 변경되었을 때 주로 발생합니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/authenticator/standard_authenticator.py`, `mju_univ_auth/fetcher/student_card_fetcher.py`, `mju_univ_auth/fetcher/student_change_log_fetcher.py`
    -   **조건**:
        1.  **SSO 로그인 정보 누락**: (`standard_authenticator.py`, `_fetch_login_page`)
            -   로그인 페이지 HTML에서 RSA 공개키(`id="public-key"`), CSRF 토큰(`id="c_r_t"`), 또는 로그인 폼(`id="signin-form"`)을 찾지 못했을 때 발생합니다.
        2.  **MSI CSRF 토큰 누락**: (`student_card_fetcher.py` 및 `student_change_log_fetcher.py`, `_get_csrf_token`)
            -   MSI 메인 페이지 HTML에서 CSRF 토큰을 담고 있는 `meta` 태그나 `input` 태그를 찾지 못했을 때 발생합니다.
        3.  **학생 정보 필드 누락**: (`student_card_fetcher.py`, `_parse_student_card` / `student_change_log_fetcher.py`, `_parse_changelog`)
            -   학생카드 또는 학적변동내역 정보가 담긴 최종 HTML 페이지에서, 필수 정보인 '학번' 필드를 찾지 못했을 때 발생합니다. 이는 페이지가 비정상적으로 로드되었거나, 정보가 없는 상태임을 의미할 수 있습니다.
-   **해결 방안**:
    -   이 에러는 대부분 명지대학교 웹사이트의 HTML 구조 변경이 원인입니다.
    -   `verbose=True` 옵션을 켜고 라이브러리를 실행하여, 에러 발생 직전의 HTML 응답 본문을 확인합니다.
    -   변경된 HTML 구조에 맞게 `mju_univ_auth` 라이브러리의 파싱 로직(`infrastructure/parser.py`)을 수정해야 합니다. (예: `id`나 `class` 이름 변경 확인)

---

## 5. 인증 및 세션 관련 에러

### `InvalidCredentialsError`

-   **설명**: 사용자가 제공한 아이디 또는 비밀번호가 잘못되었거나, 인증 과정에 실패했을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/authenticator/standard_authenticator.py`, `mju_univ_auth/fetcher/student_card_fetcher.py`
    -   **조건**:
        1.  **SSO 로그인 실패 (ID/PW 오류)**: (`standard_authenticator.py`, `_validate_login_result`)
            -   로그인 정보 제출 후, 서버가 반환한 페이지에 "비밀번호가 틀렸습니다"와 같은 명시적인 에러 메시지(`alert()` 또는 `var errorMsg`)가 포함되어 있을 때 발생합니다.
            -   로그인 실패 후, 다시 로그인 폼이 포함된 페이지로 돌아왔을 때 발생합니다.
        2.  **학생카드 2차 비밀번호 인증 실패**: (`student_card_fetcher.py`, `_execute`)
            -   학생카드 조회 시 필요한 2차 비밀번호 인증을 시도했지만, 다시 비밀번호 입력 폼이 나타나는 경우 발생합니다. 이는 SSO 로그인 시 사용한 비밀번호와 2차 인증 비밀번호가 다르거나, 서버 측 문제일 수 있습니다.
-   **해결 방안**:
    -   입력한 학번과 비밀번호가 정확한지 다시 확인합니다.
    -   MyiWeb에 직접 로그인하여 계정이 잠겼거나 비밀번호 변경이 필요한지 확인합니다.
    -   2차 인증 실패가 계속되면, MyiWeb에서 직접 비밀번호를 변경하고 다시 시도해볼 수 있습니다.

### `SessionExpiredError`

-   **설명**: SSO 로그인을 통해 얻은 세션이 만료되었거나 유효하지 않을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/fetcher/student_card_fetcher.py`, `mju_univ_auth/fetcher/student_change_log_fetcher.py`
    -   **함수**: `_get_csrf_token()`
    -   **조건**:
        -   로그인 성공 후 얻은 `requests.Session` 객체를 사용하여 MSI 서비스 페이지(예: 학생카드)에 접근하려 했으나, 세션이 만료되어 SSO 로그인 페이지(`sso.mju.ac.kr`)로 리다이렉트될 때 발생합니다.
        -   이는 보통 `MjuUnivAuth` 인스턴스로 로그인한 뒤 오랜 시간이 지난 후 `get_student_card()`와 같은 데이터 조회 메서드를 호출할 때 발생할 수 있습니다.
-   **해결 방안**:
    -   세션이 만료된 경우, `MjuUnivAuth`의 `login()`을 다시 호출하여 새로운 세션을 발급받아야 합니다.

### `SessionNotExistError`

-   **설명**: 로그인하여 세션을 생성하지 않은 상태에서 세션이 필요한 작업을 시도했을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/fetcher/base_fetcher.py` (실제 발생), `mju_univ_auth/facade.py` (결과 객체로 변환)
    -   **함수**: `BaseFetcher.fetch()`
    -   **조건**:
        -   `MjuUnivAuth` 인스턴스를 생성하고 `login()`을 호출하지 않거나 로그인이 실패한 상태에서 `get_student_card()` 또는 `get_student_changelog()`와 같은 데이터 조회 메서드를 호출할 때 발생합니다.
        -   저수준 API 사용 시, `requests.Session` 객체를 `Fetcher` 클래스에 전달하지 않고 `fetch()`를 호출할 때 `MjuUnivAuthResult` 객체에 `ErrorCode.SESSION_NOT_EXIST_ERROR`가 설정되어 반환됩니다.
-   **해결 방안**:
    -   데이터 조회 메서드를 호출하기 전에 `MjuUnivAuth.login()`을 먼저 호출하고 성공했는지 확인해야 합니다.

### `AlreadyLoggedInError`

-   **설명**: 이미 로그인된 세션에 다시 로그인을 시도할 때 발생하도록 설계된 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/exceptions.py` (정의됨)
    -   **조건**: 현재 버전에서는 `StandardAuthenticator`가 이 예외를 직접 발생시키지 않습니다. 하지만 `MjuUnivAuth` Facade는 "하나의 인스턴스, 하나의 성공적인 세션" 원칙을 따릅니다. `login()` 메서드를 한 인스턴스에서 여러 번 호출하면, 첫 호출이 성공한 이후의 호출은 실패 플래그를 설정하고 실패 결과(`MjuUnivAuthResult`)를 담은 `self`를 반환합니다.
-   **해결 방안**:
    -   새로운 로그인이 필요할 경우, 새로운 `MjuUnivAuth` 인스턴스를 생성하여 사용하십시오.

---

## 6. 서비스 관련 에러

### `ServiceNotFoundError`

-   **설명**: 지원하지 않는 서비스 이름을 사용하여 로그인을 시도했을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/authenticator/standard_authenticator.py`
    -   **함수**: `_execute_login()`
    -   **조건**: `login()` 메서드에 전달된 `service` 문자열이 `mju_univ_auth/config.py`의 `SERVICES` 딕셔너리에 없는 키일 경우 발생합니다.
-   **해결 방안**:
    -   `login()` 호출 시 `service` 파라미터가 `config.SERVICES`에 정의된 키 중 하나인지 확인합니다. (예: 'msi', 'lms', 'portal' 등)

### `InvalidServiceUsageError`

-   **설명**: 현재 로그인된 서비스에서 지원하지 않는 기능을 호출했을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/facade.py` (결과 객체로 변환), `mju_univ_auth/exceptions.py` (정의됨)
    -   **함수**: `get_student_card()`, `get_student_changelog()`
    -   **조건**:
        -   `'msi'`가 아닌 다른 서비스(예: `'lms'`)로 로그인한 세션을 가지고 `get_student_card()`와 같이 `'msi'` 서비스가 필수적인 메서드를 호출할 때 발생합니다.
        -   실제로는 예외가 throw되기보다 `MjuUnivAuthResult` 객체에 `ErrorCode.INVALID_SERVICE_USAGE_ERROR`가 설정되어 반환됩니다.
-   **해결 방안**:
    -   `get_student_card()` 또는 `get_student_changelog()`를 호출하기 전에 반드시 `login('msi')`를 통해 MSI 서비스로 로그인해야 합니다.