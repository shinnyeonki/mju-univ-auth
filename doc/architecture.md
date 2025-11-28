# 코드 아키텍처

이 문서는 `mju-univ-auth` 라이브러리의 코드 구조와 각 모듈의 역할, 그리고 핵심 동작 흐름에 대해 상세히 설명합니다.

## 1. 개요

`mju-univ-auth`는 명지대학교 학생 인증을 위한 파이썬 라이브러리입니다. 학교의 SSO(Single Sign-On) 시스템과 MyiWeb(MSI) 서비스를 자동화하여, 로그인 세션을 획득하고 학생 관련 정보(학생카드, 학적 변동 등)를 조회하는 기능을 제공합니다.

## 2. 핵심 클래스 및 역할

라이브러리의 기능은 몇 가지 핵심 클래스를 중심으로 구성됩니다.

### `MJUSSOLogin` (`sso.py`)

-   **역할**: 라이브러리의 심장부로, 명지대학교 SSO 인증 과정을 모두 처리합니다.
-   **주요 기능**:
    -   LMS, Portal, MSI 등 다양한 서비스에 대한 SSO 로그인을 수행합니다.
    -   로그인 페이지에서 RSA 공개키와 CSRF 토큰을 추출합니다.
    -   `crypto.py` 모듈을 사용하여 로그인 정보를 암호화합니다.
    -   자동화된 폼 제출, 다단계 리다이렉션(JavaScript `location.href`, `form.submit()` 포함)을 처리하여 최종 로그인 세션을 획득합니다.
-   **결과**: 인증된 `requests.Session` 객체를 반환하여 후속 요청에 사용될 수 있도록 합니다.

### `StudentCard` (`student_card.py`)

-   **역할**: 학생카드 정보를 담는 데이터 클래스(`@dataclass`)이자, 정보 조회를 위한 고수준 인터페이스입니다.
-   **주요 기능**:
    -   `fetch()` 클래스 메서드는 SSO 로그인부터 학생카드 정보 조회까지의 모든 과정을 한 번에 처리합니다.
    -   내부적으로 `MJUSSOLogin`을 호출하여 MSI 서비스 세션을 얻고, `_StudentCardFetcher`를 이용해 실제 데이터를 가져옵니다.
    -   조회된 모든 정보(학번, 성명, 학적, 주소, 사진 등)를 속성으로 가집니다.

### `BaseFetcher` (`abc.py`)

-   **역할**: MSI 서비스에서 특정 정보를 조회하는 모든 "Fetcher" 클래스들의 추상 기본 클래스(ABC)입니다.
-   **주요 기능**:
    -   `fetch()` 추상 메서드를 정의하여 하위 클래스가 데이터 조회 로직을 구현하도록 강제합니다.
    -   MSI 서비스 내에서 페이지 이동 시 필요한 CSRF 토큰을 획득하는 `_get_csrf_token()` 메서드를 공통 기능으로 제공합니다.
    -   `session`, `user_pw` 등 Fetcher에 필요한 기본 속성을 정의합니다.
-   **구현체**: `_StudentCardFetcher`가 이 클래스를 상속받아 학생카드 조회 과정을 구현합니다.

## 3. 인증 및 데이터 조회 흐름

라이브러리는 크게 두 가지 주요 흐름으로 동작합니다.

### 3.1. SSO 로그인 흐름 (`MJUSSOLogin.login`)

1.  **서비스 URL 접속**: 사용자가 지정한 서비스(예: `msi`)의 SSO 시작 URL로 GET 요청을 보냅니다.
2.  **로그인 페이지 파싱**: 응답으로 받은 HTML에서 다음 세 가지 중요 정보를 추출합니다.
    -   `public-key`: RSA 공개키 (세션키 암호화에 사용)
    -   `c_r_t`: CSRF 토큰 (로그인 요청 위조 방지)
    -   `form-action`: 로그인 데이터를 POST할 URL
3.  **데이터 암호화 (`_prepare_encrypted_data`)**:
    -   **세션키 생성**: `crypto.generate_session_key()`를 호출하여 PBKDF2로 파생된 AES 암호화 키/IV와 원본 `keyStr`을 생성합니다.
    -   **RSA 암호화**: `keyStr`과 타임스탬프를 조합하여 서버의 `public-key`로 암호화합니다. (`encsymka`)
    -   **AES 암호화**: 사용자의 비밀번호(`user_pw`)를 위에서 파생된 AES 키/IV로 암호화합니다. (`pw_enc`)
4.  **로그인 요청**: 암호화된 데이터와 CSRF 토큰을 `form-action` URL로 POST합니다.
5.  **리다이렉션 처리**: 서버는 여러 단계의 리다이렉션을 통해 최종 서비스 페이지로 사용자를 안내합니다. 이 과정에는 다음이 포함됩니다.
    -   HTTP 302 리다이렉션.
    -   JavaScript `location.href = '...'` 형태의 클라이언트 사이드 리다이렉션.
    -   JavaScript `onLoad="doLogin()"` 과 같이 페이지 로드 시 자동으로 폼을 제출하는 로직 (`_handle_js_form_submit`에서 처리).
6.  **성공 확인**: 최종 도착한 페이지의 URL이 목표 서비스의 도메인인지, 페이지 내용에 '로그아웃' 버튼이 있는지 등을 검사하여 로그인을 최종 확인합니다.

### 3.2. 학생카드 정보 조회 흐름 (`StudentCard.fetch`)

1.  **SSO 선행**: `MJUSSOLogin`을 통해 `msi` 서비스에 로그인하여 인증된 `requests.Session`을 확보합니다.
2.  **Fetcher 생성**: 이 세션과 사용자 비밀번호를 사용하여 `_StudentCardFetcher` 객체를 생성합니다.
3.  **CSRF 토큰 획득**: `BaseFetcher`의 `_get_csrf_token()`을 호출하여 MSI 메인 페이지의 CSRF 토큰을 가져옵니다.
4.  **페이지 접근**: 학생카드 메뉴 URL(`STUDENT_CARD_URL`)로 POST 요청을 보내 페이지 접근을 시도합니다.
5.  **2차 인증 처리**:
    -   만약 페이지가 비밀번호를 다시 요구하면(`_is_password_required`), `_submit_password()`가 호출되어 비밀번호를 한 번 더 제출합니다.
    -   2차 인증 성공 후 나타나는 자동 리다이렉트 폼을 `_handle_redirect_form()`에서 처리합니다.
6.  **정보 파싱 (`_parse_info`)**: 최종적으로 학생 정보가 담긴 HTML 페이지를 `BeautifulSoup`으로 파싱하여 `StudentCard` 데이터 클래스의 각 필드(학번, 이름, 학과, 사진 등)를 채웁니다.
7.  **결과 반환**: 모든 정보가 채워진 `StudentCard` 객체를 반환합니다.

## 4. 암호화 (`crypto.py`)

SSO 로그인은 자바스크립트 기반의 RSA+AES 하이브리드 암호화 방식을 사용하며, `crypto.py`는 이를 Python으로 재구현한 것입니다.

-   `generate_session_key()`: 64바이트의 랜덤 문자열(`keyStr`)을 생성하고, 이 문자열의 일부를 salt로 사용하여 PBKDF2(SHA1) 알고리즘으로 32바이트 길이의 AES 키를 파생시킵니다. 키의 마지막 16바이트는 IV로 사용됩니다.
-   `encrypt_with_rsa()`: 서버가 내려준 공개키를 사용해 `keyStr`과 타임스탬프를 PKCS1v15 방식으로 암호화합니다. 서버는 이 값을 복호화하여 `keyStr`을 얻고, 클라이언트와 동일한 방식으로 AES 키를 파생시킬 수 있습니다.
-   `encrypt_with_aes()`: `generate_session_key`에서 파생된 키와 IV를 사용하여 사용자의 실제 비밀번호를 AES-CBC 방식으로 암호화합니다.

이러한 하이브리드 방식은 안전하게 대칭키(AES 키)를 서버와 공유하고, 실제 민감 정보(비밀번호)는 대칭키로 암호화하여 전송하는 효율적이고 안전한 구조입니다.

## 5. 추상화 및 확장성 (`abc.py`)

`BaseFetcher` 추상 클래스는 `mju-univ-auth`의 확장성을 보장합니다. `StudentCard` 외에 '학적변동내역'(`StudentChangeLog`)과 같은 다른 정보를 MSI에서 조회하고 싶을 경우, 개발자는 `BaseFetcher`를 상속받는 새로운 Fetcher 클래스를 만들기만 하면 됩니다.

새로운 Fetcher는 `fetch()` 메서드 내에서 해당 정보 페이지에 접근하고 파싱하는 로직만 구현하면 되며, CSRF 토큰 획득과 같은 공통 로직은 `BaseFetcher`가 처리해주므로 코드 중복을 최소화하고 개발을 단순화할 수 있습니다.