# `mju-univ-auth` 모듈 기술 문서

## 1. 개요

`mju-univ-auth`은 명지대학교 학생 정보 시스템(mju-univ-auth, MSI)에 로그인하여 학생의 상세 정보(학생카드)를 조회하는 Python 라이브러리입니다. 이 문서는 `mju-univ-auth` 모듈의 내부 동작, 특히 클라이언트(본 라이브러리)와 명지대학교 서버 간의 요청 및 응답 흐름을 심층적으로 분석하고 설명합니다.

명지대학교의 통합 로그인(SSO) 시스템은 보안을 위해 복잡한 인증 절차를 사용합니다. 이 과정은 단순히 아이디와 비밀번호를 전송하는 것을 넘어, JavaScript 기반의 하이브리드 암호화(RSA+AES), CSRF 토큰, 여러 단계의 리다이렉션 및 자동 폼 제출을 포함합니다. `mju-univ-auth`은 이 모든 과정을 자동화하여 최종적으로 학생 정보를 추출합니다.

본 문서는 다음 두 가지 핵심 프로세스를 중심으로 설명합니다.

1.  **SSO 통합 로그인 과정**: `sso.py`와 `crypto.py`를 중심으로, 어떻게 서버로부터 암호화에 필요한 정보를 받고, 자격 증명을 안전하게 암호화하여 전송하며, 최종적으로 서비스 세션을 획득하는지 설명합니다.
2.  **학생카드 정보 조회 과정**: `student_card.py`를 중심으로, 획득한 세션을 사용하여 학생카드 페이지에 접근하고, 2차 비밀번호 인증을 거쳐, 최종적으로 HTML 페이지에서 학생 정보를 파싱하는 과정을 설명합니다.

## 2. 모듈 구조

```
mju-univ-auth/
├── __init__.py           # 패키지 초기화 및 공개 API 정의
├── __main__.py           # `python -m mju-univ-auth` 실행을 위한 CLI 엔트리포인트
├── abc.py                # 추상 기본 클래스 (BaseFetcher)
├── crypto.py             # SSO 로그인에 사용되는 RSA/AES 암호화 유틸리티
├── examples.py           # 라이브러리 사용 예제
├── exceptions.py         # 커스텀 예외 클래스
├── sso.py                # SSO 통합 로그인 자동화 클래스 (MJUSSOLogin)
├── student_card.py       # 학생카드 정보(StudentCard) 및 조회 로직
├── student_changelog.py  # 학적변동내역 정보(StudentChangeLog) 및 조회 로직
├── utils.py              # 로깅, 색상 코드 등 공통 유틸리티
└── README.md             # 본 기술 문서
```

## 3. 핵심 동작 원리: 클라이언트-서버 상호작용

`mju-univ-auth`의 모든 기능은 `requests.Session` 객체를 통해 이루어집니다. 이 세션 객체는 여러 요청에 걸쳐 쿠키를 자동으로 관리하므로, 서버와의 연속적인 통신 상태를 유지할 수 있습니다.

### 3.1. SSO 통합 로그인 과정 (`sso.py`, `crypto.py`)

SSO 로그인은 명지대학교의 여러 서비스(LMS, Portal, MSI 등)에 대한 중앙 인증을 처리합니다. 이 과정의 목표는 암호화된 자격 증명을 SSO 서버에 제출하고, 성공 시 발급되는 인증 코드를 통해 목표 서비스(여기서는 MSI)의 유효한 세션 쿠키를 획득하는 것입니다.

**전체 흐름 요약:**

`GET (Login Page)` -> `Parse Page (Get Public Key, CSRF)` -> `Client-Side Encrypt (RSA+AES)` -> `POST (Submit Encrypted Credentials)` -> `Handle Redirects (HTTP 302, JS Form Submit)` -> `Final Session`

---

#### **1단계: 로그인 페이지 접속 및 정보 획득**

-   **Client Action**: `MJUSSOLogin.login()` 메서드가 호출되면, 먼저 목표 서비스(`msi`)에 해당하는 SSO URL로 `GET` 요청을 보냅니다.
    -   **Method**: `GET`
    -   **URL**: `https://sso.mju.ac.kr/sso/auth?client_id=msi&...`
    -   **Purpose**: 로그인에 필요한 정보가 담긴 HTML 페이지를 받아옵니다.

-   **Server Response**: 서버는 HTTP `200 OK`와 함께 로그인 폼이 포함된 HTML 페이지를 응답합니다. 이 페이지에는 눈에 보이지 않는 중요한 정보들이 숨겨져 있습니다.

-   **Client Action (Parsing)**: `_parse_login_page()` 메서드가 응답받은 HTML을 파싱하여 다음 정보를 추출합니다.
    1.  **RSA 공개키 (`public-key`)**:
        -   HTML 내 `<input type="hidden" id="public-key" value="...">` 태그에 Base64로 인코딩된 형태로 존재합니다.
        -   이 공개키는 클라이언트에서 생성한 대칭키(세션키)를 암호화하여 서버로 안전하게 전송하는 데 사용됩니다. (키 교환)
    2.  **CSRF 토큰 (`c_r_t`)**:
        -   `<input type="hidden" id="c_r_t" value="...">` 태그에 존재합니다.
        -   Cross-Site Request Forgery 공격을 방지하기 위한 토큰으로, 로그인 요청 시 반드시 포함되어야 합니다.
    3.  **폼 액션 URL (`form_action`)**:
        -   `<form id="signin-form" action="...">` 태그의 `action` 속성값입니다.
        -   암호화된 로그인 정보를 `POST`할 대상 URL입니다.

---

#### **2단계: 클라이언트 측 하이브리드 암호화 (`crypto.py`)**

서버로 비밀번호를 직접 보내는 대신, 실제 웹사이트의 JavaScript 코드(`bandiJS`) 동작을 그대로 모방한 하이브리드 암호화 방식을 사용합니다. 이는 대칭키 암호화(AES)의 속도와 비대칭키 암호화(RSA)의 보안성을 결합한 것입니다. 이 과정은 `_prepare_encrypted_data()` 메서드 내에서 `crypto.py`의 함수들을 호출하여 수행됩니다.

1.  **세션키 생성 (`generate_session_key`)**:
    -   먼저, 일회용 대칭키로 사용할 **세션키(Session Key)**를 생성합니다.
    -   `forge.random.getBytesSync(64)`에 해당하는 로직으로 64바이트의 랜덤 데이터를 생성합니다.
    -   이 데이터를 Base64로 인코딩하여 `keyStr` (문자열)을 만듭니다.
    -   `keyStr`의 마지막 16바이트를 `salt`로 사용합니다.
    -   `PBKDF2` (Password-Based Key Derivation Function 2) 알고리즘을 사용하여 `keyStr`와 `salt`로부터 최종적인 AES 암호화 키(`key`)와 초기화 벡터(`iv`)를 파생시킵니다.
        -   Hash: SHA1
        -   Iterations: 1024
        -   Key Length: 32 bytes
    -   이 함수는 `{ 'keyStr': ..., 'key': ..., 'iv': ... }` 딕셔너리를 반환합니다.

2.  **키 교환: 세션키 암호화 (`encrypt_with_rsa`)**:
    -   서버는 클라이언트가 어떤 세션키를 사용했는지 알아야 비밀번호를 복호화할 수 있습니다. 이때 세션키(`keyStr`)를 안전하게 전송하기 위해 1단계에서 얻은 **RSA 공개키**를 사용합니다.
    -   `keyStr`와 현재 타임스탬프를 쉼표(`,`)로 연결한 문자열(예: `"Abc...def,167...987"`)을 만듭니다.
    -   이 문자열을 RSA-PKCS1-v1.5 방식으로 암호화합니다.
    -   암호화된 결과는 Base64로 인코딩되어 `encsymka`라는 이름의 필드에 담깁니다.

3.  **데이터 암호화: 비밀번호 암호화 (`encrypt_with_aes`)**:
    -   이제 실제 사용자 비밀번호를 위에서 파생된 **AES 키와 IV**를 사용하여 암호화합니다.
    -   JavaScript 코드와의 호환성을 위해, 비밀번호를 먼저 Base64로 인코딩합니다.
    -   이 Base64 인코딩된 데이터를 AES-256-CBC 방식으로 암호화하고, 그 결과를 다시 Base64로 인코딩합니다.
    -   이 최종 결과가 `pw_enc`라는 필드에 담깁니다.

---

#### **3단계: 암호화된 로그인 정보 전송**

-   **Client Action**: `login()` 메서드는 2단계에서 준비된 암호화 데이터를 `POST` 요청의 본문(form data)에 담아 1단계에서 추출한 `form_action` URL로 전송합니다.
    -   **Method**: `POST`
    -   **URL**: `https://sso.mju.ac.kr/sso/api/v1/auth/sign-in-proc` (또는 유사한 경로)
    -   **Headers**:
        -   `Content-Type`: `application/x-www-form-urlencoded`
        -   `Referer`: `https://sso.mju.ac.kr/sso/auth?...` (이전 페이지)
        -   `Origin`: `https://sso.mju.ac.kr`
    -   **Form Data**:
        -   `user_id`: 사용자 아이디 (평문)
        -   `pw`: 빈 문자열 (사용 안 함)
        -   `pw_enc`: AES로 암호화된 비밀번호
        -   `encsymka`: RSA로 암호화된 세션키 정보
        -   `c_r_t`: CSRF 토큰
        -   `user_id_enc`: 빈 문자열 (사용 안 함)

-   **Server Action**:
    1.  서버는 `encsymka`를 자신의 RSA **비공개키**로 복호화하여 `keyStr`와 타임스탬프를 얻습니다.
    2.  `keyStr`를 이용해 클라이언트와 동일한 방식으로 PBKDF2를 실행하여 AES `key`와 `iv`를 복원합니다.
    3.  복원된 AES 키로 `pw_enc`를 복호화하여 사용자 비밀번호를 얻습니다.
    4.  `user_id`와 복호화된 비밀번호가 일치하는지 확인합니다.

---

#### **4단계: 리다이렉션 처리 및 세션 획득**

인증에 성공하면, 서버는 사용자를 원래 요청했던 서비스(MSI)로 보내주기 위해 여러 번의 리다이렉션을 수행합니다. `requests` 라이브러리의 `allow_redirects=True` 옵션과 커스텀 로직을 통해 이 과정을 자동으로 처리합니다.

-   **Server Response (Type 1: HTTP 302 Redirect)**
    -   서버는 HTTP `302 Found` 응답과 함께 `Location` 헤더에 다음 이동할 URL을 명시합니다. 이 URL에는 SSO 서버가 발급한 임시 **Authorization Code**가 포함될 수 있습니다.
    -   예: `Location: https://msi.mju.ac.kr/index_Myiweb.jsp?code=...`
    -   클라이언트(`requests.Session`)는 이 `Location` 헤더를 자동으로 따라가 다음 요청을 보냅니다.

-   **Server Response (Type 2: JavaScript 자동 폼 제출)**
    -   일부 페이지는 HTTP 리다이렉션 대신, 페이지 로드 시(`onLoad`) JavaScript로 폼을 자동 제출하는 방식을 사용합니다.
        ```html
        <body onLoad="doLogin()">
            <form name="form1" action="/servlet/login_security" method="post">
                <input name="code" value="..."/>
                <input name="_csrf" value="..."/>
            </form>
            <script> function doLogin() { document.form1.submit(); } </script>
        </body>
        ```
    -   **Client Action (`_handle_js_form_submit`)**:
        -   `sso.py`는 응답받은 HTML에 `onLoad=`나 `submit()` 같은 키워드가 있는지 감지합니다.
        -   `BeautifulSoup`으로 HTML을 파싱하여 `<form>` 태그의 `action` URL과 내부 `<input>` 필드들을 추출합니다.
        -   추출한 데이터로 새로운 `POST` 요청을 만들어 전송함으로써, 브라우저의 JavaScript 동작을 흉내 냅니다.

-   **Server Response (Type 3: JavaScript `location.href` 리다이렉트)**
    -   또 다른 형태는 `<script>location.href='...'</script>`와 같이 JavaScript를 통해 페이지를 이동시키는 방식입니다.
    -   **Client Action**: `sso.py`는 정규 표현식(`re.search`)을 사용해 `location.href` 패턴을 감지하고, 지정된 URL로 `GET` 요청을 보내 리다이렉션을 수동으로 처리합니다.

-   **Final Result**:
    -   이 모든 리다이렉션 과정이 끝나면, 클라이언트의 `requests.Session` 객체에는 최종 서비스(`msi.mju.ac.kr`)에서 사용 가능한 유효한 세션 쿠키(예: `JSESSIONID`)가 저장됩니다.
    -   `login()` 메서드는 `success=True`와 함께 이 세션 객체를 담은 `LoginResult`를 반환합니다. 만약 로그인 과정 중 서버로부터 에러 메시지(예: `alert('비밀번호가 틀렸습니다')`)가 반환되면, 이를 파싱하여 `success=False`와 함께 에러 메시지를 반환합니다.

<br>

### 3.2. 학생카드 정보 조회 과정 (`student_card.py`)

SSO 로그인을 통해 `msi.mju.ac.kr` 도메인의 유효한 세션을 획득한 후, 실제 학생 정보를 가져오는 단계입니다. 이 과정은 보안을 위해 추가적인 비밀번호 인증을 요구합니다.

**전체 흐름 요약:**

`GET (MSI Home, Get CSRF)` -> `POST (Request Student Card Page)` -> `Parse Page (Check for Password Form)` -> `POST (Submit Password Plaintext)` -> `Handle Redirect Form` -> `Parse Final Page (Extract Student Info)`

---

#### **1단계: MSI CSRF 토큰 획득**

-   **Client Action**: `StudentCardFetcher.fetch()` 메서드는 가장 먼저 `_get_csrf_token()`을 호출하여 MSI 서비스의 메인 페이지에 `GET` 요청을 보냅니다.
    -   **Method**: `GET`
    -   **URL**: `https://msi.mju.ac.kr/servlet/security/MySecurityStart`
    -   **Purpose**: SSO 로그인 과정에서 얻은 세션 쿠키를 사용하여 MSI 서버에 첫 연결을 시도하고, 학생카드 조회에 필요한 **별도의 CSRF 토큰**을 획득합니다. MSI 애플리케이션은 SSO와는 다른 CSRF 토큰을 사용합니다.

-   **Server Response**: 현재 세션이 유효하다면, 서버는 MSI 메인 페이지의 HTML을 반환합니다.

-   **Client Action (Parsing)**: `_extract_csrf_from_html()`은 정규 표현식을 사용해 응답 HTML에서 CSRF 토큰을 추출합니다. 이 토큰은 `<meta name="_csrf" content="...">` 또는 `<input type="hidden" name="_csrf" value="...">` 형태로 존재합니다.

---

#### **2단계: 학생카드 페이지 접근 요청**

-   **Client Action**: `_access_student_card_page()` 메서드는 실제 웹사이트에서 사용자가 '학생카드' 메뉴를 클릭했을 때 발생하는 요청을 시뮬레이션합니다. 이는 일반적인 페이지 이동이 아닌, 특정 데이터를 포함한 `POST` 요청입니다.
    -   **Method**: `POST`
    -   **URL**: `https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard`
    -   **Headers**:
        -   `X-CSRF-TOKEN`: 1단계에서 획득한 CSRF 토큰
        -   `Content-Type`, `Referer`, `Origin` 등
    -   **Form Data**:
        -   `pgmid`: `W_SUD005` (학생카드 프로그램 ID)
        -   `_csrf`: CSRF 토큰
        -   기타 시스템 식별자 (`sysdiv`, `subsysdiv` 등)

-   **Server Response**: 서버는 이 요청을 받고, 중요한 정보에 접근하기 전 사용자를 재인증하기 위해 **비밀번호를 다시 입력하는 폼**이 포함된 HTML 페이지를 반환합니다.

---

#### **3단계: 2차 비밀번호 인증**

-   **Client Action**: `_check_password_required()`가 응답 HTML에 비밀번호 입력 필드(`tfpassword`)가 있는지 확인합니다. 확인되면 `_submit_password()`가 호출됩니다.
    -   **Method**: `POST`
    -   **URL**: `https://msi.mju.ac.kr/servlet/sys/sys15/Sys15Svl01verifyPW`
    -   **Purpose**: 비밀번호를 서버로 보내 2차 인증을 수행합니다.
    -   **Form Data**:
        -   `tfpassword`: **사용자 비밀번호 (평문)**. 이 단계에서는 SSO와 달리 암호화되지 않은 비밀번호가 그대로 전송됩니다.
        -   `originalurl`: 인증 성공 후 이동할 URL (학생카드 페이지 URL)
        -   `_csrf`: CSRF 토큰

-   **Server Response**: 비밀번호가 올바르면, 서버는 다음 단계로 이동하기 위한 중간 페이지를 응답합니다. 이 페이지는 최종 목적지로 이동하기 위한 또 다른 자동 제출 폼을 포함하고 있습니다. 비밀번호가 틀리면 에러 메시지가 담긴 페이지를 반환합니다.

---

#### **4단계: 리다이렉트 폼 처리**

-   **Client Action**: `_handle_redirect_form()`은 3단계의 응답으로 받은 HTML을 처리합니다. 이 HTML에는 3.1절의 4단계에서 설명한 것과 유사한 JavaScript 자동 제출 폼이 들어있습니다.
    ```html
    <form name="form1" action="https://msi.mju.ac.kr/servlet/su/sum/Sum00Svl01getStdCard">
        <input type="hidden" name="_csrf" value="...">
    </form>
    <script> document.form1.submit(); </script>
    ```
    -   클라이언트는 이 폼의 `action` URL과 `_csrf` 토큰을 파싱하여, 최종 학생카드 페이지로 `POST` 요청을 한 번 더 보냅니다.

-   **Server Response**: 모든 인증 절차를 통과했으므로, 서버는 마침내 **학생의 모든 정보가 담긴 최종 HTML 페이지**를 응답합니다.

---

#### **5단계: 학생 정보 파싱**

-   **Client Action**: `_parse_student_info()` 메서드가 최종적으로 받은 HTML 페이지를 `BeautifulSoup`을 이용해 파싱합니다.
    -   페이지는 `flex-table-item` 클래스를 가진 `div`들로 구조화되어 있으며, 각 `div`는 '학번', '한글성명' 등의 항목명(`item-title`)과 값(`item-data`)을 포함합니다.
    -   루프를 돌며 각 항목을 순회하고, 제목에 따라 `StudentInfo` 데이터 클래스의 해당 필드에 값을 저장합니다.
    -   값은 일반 텍스트일 수도 있고, `input` 태그의 `value` 속성에 들어있을 수도 있습니다. 코드는 두 경우를 모두 처리합니다.
    -   학생 사진은 `<img>` 태그의 `src` 속성에 `data:image/jpg;base64,...` 형태로 포함된 Base64 데이터를 직접 추출합니다.
    -   파싱이 완료되면 모든 정보가 채워진 `StudentInfo` 객체를 반환합니다.

## 4. 결론

`mju-univ-auth` 모듈은 명지대학교 SSO와 MSI 시스템의 복잡한 클라이언트-서버 통신 과정을 Python 코드로 정교하게 재현한 결과물입니다. 핵심은 다음과 같습니다.

1.  **정확한 순서 준수**: 각 단계의 요청은 이전 단계의 응답(쿠키, CSRF 토큰, 리다이렉션 URL 등)에 의존하므로, 정해진 순서를 반드시 따라야 합니다.
2.  **JavaScript 동작 모방**: 실제 브라우저에서 실행되는 JavaScript의 동작(암호화, 폼 제출, 리다이렉션)을 서버와의 HTTP 요청/응답만으로 시뮬레이션하는 것이 핵심 기술입니다.
3.  **상태 관리**: `requests.Session`을 통해 여러 도메인(`sso.mju.ac.kr`, `msi.mju.ac.kr`)에 걸친 쿠키를 자동으로 관리하여 로그인 상태를 유지합니다.
4.  **동적 파싱**: 서버 응답이 변경될 수 있으므로, HTML 구조에 의존하는 파싱 로직(CSRF 토큰, 폼 데이터, 학생 정보 추출)은 `BeautifulSoup`과 정규 표현식을 통해 유연하게 대처합니다.

이 문서를 통해 `mju-univ-auth`이 어떻게 명지대학교 웹 서비스와 상호작용하는지에 대한 깊이 있는 이해를 얻을 수 있기를 바랍니다.