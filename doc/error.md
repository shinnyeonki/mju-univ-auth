# `mju_univ_auth` 모듈 에러 상세 문서

이 문서는 `mju_univ_auth` 라이브러리 사용 중 발생할 수 있는 모든 커스텀 예외(Exception)에 대해 상세히 설명합니다. 각 에러가 어떤 상황에서, 어떤 조건으로 발생하는지, 그리고 가능한 해결 방안은 무엇인지 안내합니다.

## 1. 에러 클래스 계층 구조

`mju_univ_auth`의 모든 커스텀 에러는 `MjuUnivAuthError`를 상속받습니다.

```
MjuUnivAuthError
├── NetworkError
├── PageParsingError
├── InvalidCredentialsError
└── SessionExpiredError
```

---

## 2. 공통 에러 (Common Errors)

### `MjuUnivAuthError`

-   **설명**: `mju_univ_auth` 라이브러리에서 발생하는 모든 문제에 대한 최상위 기본 예외 클래스입니다. 보통 더 구체적인 하위 에러 클래스로 발생하지만, 특정할 수 없는 문제가 생겼을 때 직접 발생할 수 있습니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/sso.py`
    -   **함수**: `MJUSSOLogin.login()`
    -   **조건**:
        1.  `login()` 메서드에 지원되지 않는 `service` 이름(예: 'lms', 'msi' 외의 값)이 인자로 전달되었을 때 발생합니다.
        2.  SSO 로그인 성공/실패 여부를 명확히 판단할 수 없는 예외적인 상태일 때 발생합니다. (예: 서버 응답에 에러 메시지도 없고, 성공적인 리다이렉션도 아닌 경우)
-   **해결 방안**:
    -   `login()` 호출 시 `service` 파라미터가 `MJUSSOLogin.SERVICES` 딕셔너리에 정의된 키 중 하나인지 확인합니다.
    -   로그인 결과가 불확실한 경우, `verbose=True` 옵션을 켜서 상세 로그를 확인하고, 명지대학교 웹 서비스의 동작이 변경되었는지 점검해야 합니다.

---

## 3. 네트워크 관련 에러

### `NetworkError`

-   **설명**: 명지대학교 서버와의 HTTP 통신 과정에서 문제가 발생했을 때 발생하는 예외입니다. 주로 `requests.RequestException`을 감싸서 발생시킵니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/sso.py`, `mju_univ_auth/student_card.py`, `mju_univ_auth/student_changelog.py`, `mju_univ_auth/abc.py`
    -   **조건**:
        1.  **SSO 로그인 페이지 접속 실패**: (`sso.py`, `login`)
            -   `requests.get()` 호출 중 DNS 조회 실패, 연결 거부, 타임아웃 등이 발생할 때.
        2.  **암호화된 로그인 정보 전송 실패**: (`sso.py`, `login`)
            -   `requests.post()`로 암호화된 자격 증명을 전송하는 과정에서 네트워크 문제가 발생할 때.
        3.  **CSRF 토큰 획득 실패**: (`abc.py`, `_get_csrf_token`)
            -   MSI 메인 페이지(`MySecurityStart`)에 접속하여 CSRF 토큰을 가져오는 과정에서 네트워크 문제가 발생할 때.
        4.  **학생카드/학적변동내역 페이지 접근 실패**: (`student_card.py`, `student_changelog.py`)
            -   로그인 후, 각 정보 페이지에 `POST` 요청을 보내는 과정에서 네트워크 문제가 발생할 때.
        5.  **2차 비밀번호 인증 실패**: (`student_card.py`, `_submit_password`)
            -   학생카드 조회 시, 2차 비밀번호를 전송하는 과정에서 네트워크 문제가 발생할 때.
-   **해결 방안**:
    -   인터넷 연결 상태를 확인합니다.
    -   방화벽이나 프록시가 명지대학교 서버(`sso.mju.ac.kr`, `msi.mju.ac.kr`)로의 연결을 차단하고 있는지 확인합니다.
    -   명지대학교 서버가 점검 중이거나 일시적으로 다운되었을 수 있으니, 잠시 후 다시 시도합니다.

---

## 4. 페이지 파싱 관련 에러

### `PageParsingError`

-   **설명**: 서버로부터 받은 HTML 응답을 분석(파싱)하여 필요한 정보를 추출하는 데 실패했을 때 발생하는 예외입니다. 이는 명지대학교 웹 페이지의 구조가 변경되었을 때 주로 발생합니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/sso.py`, `mju_univ_auth/student_card.py`, `mju_univ_auth/student_changelog.py`, `mju_univ_auth/abc.py`
    -   **조건**:
        1.  **SSO 로그인 정보 누락**: (`sso.py`, `_parse_login_page`)
            -   로그인 페이지 HTML에서 RSA 공개키(`id="public-key"`), CSRF 토큰(`id="c_r_t"`), 또는 로그인 폼(`id="signin-form"`)을 찾지 못했을 때 발생합니다.
        2.  **MSI CSRF 토큰 누락**: (`abc.py`, `_get_csrf_token`)
            -   MSI 메인 페이지 HTML에서 CSRF 토큰을 담고 있는 `meta` 태그나 `input` 태그를 찾지 못했을 때 발생합니다.
        3.  **학생 정보 필드 누락**: (`student_card.py`, `_parse_info` / `student_changelog.py`, `_parse_info`)
            -   학생카드 또는 학적변동내역 정보가 담긴 최종 HTML 페이지에서, 필수 정보인 '학번' 필드를 찾지 못했을 때 발생합니다. 이는 페이지가 비정상적으로 로드되었거나, 정보가 없는 상태임을 의미할 수 있습니다.
-   **해결 방안**:
    -   이 에러는 대부분 명지대학교 웹사이트의 HTML 구조 변경이 원인입니다.
    -   `verbose=True` 옵션을 켜고 라이브러리를 실행하여, 에러 발생 직전의 HTML 응답 본문을 확인합니다.
    -   변경된 HTML 구조에 맞게 `mju_univ_auth` 라이브러리의 파싱 로직(BeautifulSoup 또는 정규표현식)을 수정해야 합니다. (예: `id`나 `class` 이름 변경 확인)

---

## 5. 인증 관련 에러

### `InvalidCredentialsError`

-   **설명**: 사용자가 제공한 아이디 또는 비밀번호가 잘못되었거나, 인증 과정에 실패했을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/sso.py`, `mju_univ_auth/student_card.py`
    -   **조건**:
        1.  **SSO 로그인 실패 (ID/PW 오류)**: (`sso.py`, `login`)
            -   로그인 정보 제출 후, 서버가 반환한 페이지에 "비밀번호가 틀렸습니다"와 같은 명시적인 에러 메시지(`alert()` 또는 `var errorMsg`)가 포함되어 있을 때 발생합니다.
            -   로그인 실패 후, 다시 로그인 폼이 포함된 페이지로 돌아왔을 때 발생합니다.
        2.  **학생카드 2차 비밀번호 인증 실패**: (`student_card.py`, `fetch`)
            -   학생카드 조회 시 필요한 2차 비밀번호 인증을 시도했지만, 다시 비밀번호 입력 폼이 나타나는 경우 발생합니다. 이는 SSO 로그인 시 사용한 비밀번호와 2차 인증 비밀번호가 다르거나, 서버 측 문제일 수 있습니다. (현재 로직 상으로는 동일한 비밀번호를 사용)
-   **해결 방안**:
    -   입력한 학번과 비밀번호가 정확한지 다시 확인합니다.
    -   MyiWeb에 직접 로그인하여 계정이 잠겼거나 비밀번호 변경이 필요한지 확인합니다.
    -   2차 인증 실패가 계속되면, MyiWeb에서 직접 비밀번호를 변경하고 다시 시도해볼 수 있습니다.

### `SessionExpiredError`

-   **설명**: SSO 로그인을 통해 얻은 세션이 만료되었거나 유효하지 않을 때 발생하는 예외입니다.
-   **발생 상황 및 조건**:
    -   **파일**: `mju_univ_auth/abc.py`
    -   **함수**: `BaseFetcher._get_csrf_token()`
    -   **조건**:
        -   로그인 성공 후 얻은 `requests.Session` 객체를 사용하여 MSI 서비스 페이지(예: 학생카드)에 접근하려 했으나, 세션이 만료되어 SSO 로그인 페이지(`sso.mju.ac.kr`)로 리다이렉트될 때 발생합니다.
        -   이는 보통 `StudentCard.fetch()`나 `StudentChangeLog.fetch()`를 직접 호출하지 않고, `MJUSSOLogin`으로 세션을 얻은 뒤 오랜 시간이 지난 후 해당 세션으로 다른 작업을 시도할 때 발생할 수 있습니다.
-   **해결 방안**:
    -   `fetch` 메서드(`StudentCard.fetch`, `StudentChangeLog.fetch`)는 내부적으로 로그인부터 모든 과정을 처리하므로 이 에러가 거의 발생하지 않습니다.
    -   만약 저수준 API를 사용하여 세션을 직접 관리하는 경우, 세션이 만료되었다면 `MJUSSOLogin.login()`을 다시 호출하여 새로운 세션을 발급받아야 합니다.
