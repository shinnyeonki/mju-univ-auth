# 라이브러리 동시성 처리 가이드

명지대학교 통합 인증(SSO) 서버는 **"하나의 계정당 하나의 활성 세션"**만 허용하는 정책을 가지고 있습니다. 즉, 특정 ID로 새로운 로그인이 발생하면, 이전에 유지되던 세션은 강제로 무효화됩니다.

이 정책은 라이브러리를 동시에 여러 스레드 또는 프로세스에서 사용할 때 예상치 못한 문제를 일으킬 수 있습니다. 이 문서는 동시성 유형에 따라 문제를 분석하고 올바른 해결 패턴을 안내합니다.

## 1. 서로 다른 사용자의 동시 요청: 병렬 처리

서로 다른 학번(예: `601XXXXX`, `602XXXXX`)으로 여러 요청이 동시에 들어오는 경우는 가장 간단한 시나리오입니다.

-   **동작 원리**: 각 `MjuUnivAuth` 인스턴스는 내부적으로 독립된 HTTP 클라이언트(세션)를 가집니다. 따라서 서로 다른 사용자의 인증 요청은 상호 간섭 없이 독립적으로 수행됩니다.
-   **결론**: 별도의 동기화 로직 없이 **완벽한 병렬(Parallel) 처리**가 가능합니다. 애플리케이션의 리소스가 허용하는 한, 여러 요청을 동시에 처리하여 전체 처리량을 높일 수 있습니다.

```python
# 예시: 여러 다른 사용자를 스레드로 동시에 처리
import threading
from mju_univ_auth import MjuUnivAuth

def fetch_student_card(user_id, user_pw):
    try:
        auth = MjuUnivAuth(user_id, user_pw)
        card = auth.get_student_card()
        print(f"{user_id}: 학생증 조회 성공")
    except Exception as e:
        print(f"{user_id}: 오류 발생 - {e}")

# 서로 다른 사용자 정보
users = [
    ("60111111", "pw1"),
    ("60222222", "pw2"),
    ("60333333", "pw3"),
]

threads = []
for user_id, user_pw in users:
    thread = threading.Thread(target=fetch_student_card, args=(user_id, user_pw))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

```

## 2. 동일한 사용자의 동시 요청: 직렬화 및 인스턴스 재사용

문제는 **동일한 학번**으로 짧은 시간 안에 여러 요청이 동시에 들어올 때 발생합니다.

-   **문제 상황 (Race Condition)**:
    1.  `스레드 A`가 `60123456` 계정으로 로그인에 성공하고 세션 `A`를 발급받습니다.
    2.  `스레드 A`가 학생 정보를 파싱하려는 찰나, `스레드 B`가 동일한 계정으로 로그인에 성공하여 세션 `B`를 발급받습니다.
    3.  이 순간 명지대 서버는 세션 `A`를 무효화합니다.
    4.  `스레드 A`는 만료된 세션 `A`로 데이터를 요청하게 되고, 인증 실패 오류를 마주합니다.
-   **결론**: 대부분의 요청이 실패하고, 인증 서버에 불필요한 부하만 가중시키게 됩니다. 따라서 동일 사용자에 대한 동시 요청은 병렬로 처리해서는 안 되며, **접근을 제어**하고 **인증된 인스턴스를 재사용**해야 합니다.

### 해결책: 사용자 ID 기반 Lock 및 인스턴스 관리

이 문제를 해결하기 위해, 라이브러리 사용자는 애플리케이션 레벨에서 다음과 같은 패턴을 구현해야 합니다. **(주의: 아래 코드는 라이브러리에 내장된 기능이 아닌, 사용자가 직접 구현해야 하는 예시입니다.)**

1.  **사용자 ID별 잠금(Lock) 구현**: 특정 ID에 대한 작업은 한 번에 하나의 스레드만 수행하도록 `threading.Lock`을 사용합니다.
2.  **인스턴스 저장 및 재사용**: 인증이 완료된 `MjuUnivAuth` 인스턴스를 메모리(예: `dict`)에 저장합니다. 동일한 ID로 새로운 요청이 오면, 새 인스턴스를 만드는 대신 기존 인스턴스를 재사용하여 불필요한 로그인을 방지합니다.
3.  **세션 유효성 검사**: 재사용하려는 인스턴스의 세션이 만료되었을 수 있으므로, `is_session_valid()` 와 같은 메서드로 유효성을 확인하고, 만료 시 락 안에서 안전하게 재인증을 수행합니다.

### 예시: 동일 사용자 요청을 안전하게 처리하는 관리자 클래스

다음은 API 서버와 같은 환경에서 동일 사용자 요청을 안전하게 처리하기 위한 관리자 클래스 구현 예시입니다.

```python
import threading
import logging
from typing import Dict
from mju_univ_auth import MjuUnivAuth, MjuAuthError, SessionExpiredError

class MjuAuthManager:
    """
    동일 사용자 동시 요청 문제를 해결하기 위한 관리자 클래스 예시.
    사용자 ID별로 MjuUnivAuth 인스턴스와 Lock을 관리합니다.
    """
    def __init__(self):
        # 사용자 ID를 키로 하여 인증된 MjuUnivAuth 인스턴스를 저장
        self._instances: Dict[str, MjuUnivAuth] = {}
        # 사용자 ID별 Lock 객체를 저장
        self._locks: Dict[str, threading.Lock] = {}
        # _locks 딕셔너리 자체의 thread-safety를 위한 글로벌 락
        self._global_lock = threading.Lock()

    def _get_user_lock(self, user_id: str) -> threading.Lock:
        """사용자 ID에 해당하는 Lock을 가져오거나 새로 생성합니다."""
        with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = threading.Lock()
            return self._locks[user_id]

    def get_auth_instance(self, user_id: str, user_pw: str) -> MjuUnivAuth:
        """
        안전하게 MjuUnivAuth 인스턴스를 가져옵니다.
        인스턴스가 없거나 세션이 만료되면 새로 생성(로그인)합니다.
        """
        user_lock = self._get_user_lock(user_id)

        with user_lock:
            # 1. 인스턴스가 존재하고 세션이 유효한지 확인
            if user_id in self._instances:
                auth = self._instances[user_id]
                try:
                    if auth.is_session_valid():
                        # 비밀번호가 변경되었을 수 있으므로 확인
                        if auth.is_password_correct(user_pw):
                            return auth
                        else:
                            logging.warning(f"[{user_id}] 비밀번호 변경됨. 재인증 필요.")
                    else:
                        logging.info(f"[{user_id}] 세션 만료됨. 재인증 필요.")
                except SessionExpiredError:
                    logging.info(f"[{user_id}] 세션 만료됨 (is_session_valid 체크 중 예외 발생). 재인증 필요.")


            # 2. 인스턴스가 없거나, 세션이 만료되었거나, 비밀번호가 틀리면 새로 로그인
            logging.info(f"[{user_id}] 새 인스턴스 생성 및 로그인 시도.")
            try:
                # MjuUnivAuth 생성 시 자동으로 로그인이 수행됩니다.
                new_auth = MjuUnivAuth(user_id, user_pw)
                self._instances[user_id] = new_auth
                return new_auth
            except MjuAuthError as e:
                logging.error(f"[{user_id}] 인증 실패: {e}")
                # 실패 시 기존에 있던 인스턴스도 제거하는 것이 안전
                if user_id in self._instances:
                    del self._instances[user_id]
                raise

    def get_student_card_safe(self, user_id: str, user_pw: str):
        """위의 관리 로직을 사용하여 안전하게 학생증 정보를 조회합니다."""
        try:
            auth_instance = self.get_auth_instance(user_id, user_pw)
            # Fetch-with-Retry 로직이 내장되어 있어 세션 만료에 대응 가능
            return auth_instance.get_student_card()
        except MjuAuthError as e:
            # 인증 오류를 그대로 전달하거나 애플리케이션에 맞게 처리
            raise e

```

### 요약

-   **서로 다른 사용자**: 걱정 없이 병렬로 처리하세요.
-   **동일한 사용자**: 반드시 접근 제어가 필요합니다. 매번 새 인스턴스를 생성하지 말고, 위 예시와 같이 사용자별로 **인스턴스를 관리하고 재사용**하는 로직을 애플리케이션에 구현하세요.