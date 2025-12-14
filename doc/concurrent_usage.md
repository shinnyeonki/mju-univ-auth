# 동시성 사용 팁

명지대학교 SSO 시스템은 "중복 로그인 방지(Single Active Session)" 정책을 사용하기 때문에, 같은 ID로 새로운 로그인이 발생하면 서버는 기존 세션 쿠키를 무효화합니다. 이로 인해 동시 요청 시 문제가 발생할 수 있습니다.

## 문제 분석

라이브러리를 사용할 때 같은 사용자 ID로 여러 스레드나 프로세스에서 동시에 `MjuUnivAuth` 인스턴스를 생성하고 로그인하면, 서버가 이전 세션을 죽여버려 동시 실행 중인 다른 요청이 실패합니다.

## 해결책: 세션 재사용 패턴

### 권장 접근 방식

1. **세션 재사용**: Python의 `requests.Session`은 Thread-safe하므로, 한 번 로그인된 인스턴스를 여러 스레드에서 재사용하세요.
2. **싱글톤 관리**: 사용자 ID별로 하나의 `MjuUnivAuth` 인스턴스를 유지하고 재사용합니다.
3. **락킹**: 로그인 과정만 동기화하고, 데이터 조회는 병렬로 수행합니다.

### 예시: AuthManager 구현

API 서버 측에서 사용할 수 있는 매니저 클래스 예시입니다.

```python
import threading
import logging
from typing import Dict
from mju_univ_auth import MjuUnivAuth

class MjuAuthManager:
    def __init__(self):
        self._instances: Dict[str, MjuUnivAuth] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_user_lock(self, user_id: str) -> threading.Lock:
        with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = threading.Lock()
            return self._locks[user_id]

    def get_student_card_safe(self, user_id: str, user_pw: str):
        user_lock = self._get_user_lock(user_id)

        with user_lock:
            if user_id not in self._instances:
                self._instances[user_id] = MjuUnivAuth(user_id=user_id, user_pw=user_pw)
            auth = self._instances[user_id]

        # 세션 유효성 먼저 체크
        if not auth.is_session_valid():
            logging.info(f"세션 만료, 재로그인: {user_id}")
            with user_lock:
                self._instances[user_id] = MjuUnivAuth(user_id=user_id, user_pw=user_pw)
                auth = self._instances[user_id]

        return auth.get_student_card()

auth_manager = MjuAuthManager()

def get_student_card(user_id: str, user_pw: str):
    result = auth_manager.get_student_card_safe(user_id, user_pw)
    # 결과 처리...
```

## 요약

- 같은 ID로 매번 새 인스턴스를 생성하지 말고 재사용하세요.
- 로그인 과정만 동기화하고, 조회는 병렬 수행 가능합니다.
- 세션 만료 시 자동 재로그인 로직을 구현하세요.
