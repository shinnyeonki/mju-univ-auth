# 고급 사용법 (저수준 API)

저수준 API는 개별 컴포넌트를 직접 제어해야 할 때 사용합니다. 스크립트 개발이나 디버깅 시 유용합니다.

### 4.1. StandardAuthenticator로 세션 획득

`StandardAuthenticator` 클래스는 SSO 로그인만을 담당합니다:

```python
from mju_univ_auth import StandardAuthenticator

# 인증 객체 생성
authenticator = StandardAuthenticator(
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
from mju_univ_auth import StandardAuthenticator, StudentCardFetcher

# 1. 먼저 세션 획득
authenticator = StandardAuthenticator("학번", "비밀번호")
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
from mju_univ_auth import StandardAuthenticator, StudentChangeLogFetcher

# 1. 세션 획득
authenticator = StandardAuthenticator("학번", "비밀번호")
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
