# mju-univ-auth

명지대학교 통합 인증(SSO) 및 학생 정보 조회 Python 라이브러리

[![PyPI version](https://badge.fury.io/py/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)
[![Python](https://img.shields.io/pypi/pyversions/mju-univ-auth.svg)](https://pypi.org/project/mju-univ-auth/)

## 1. 목적

이 라이브러리는 명지대학교 학생들이 프로그래밍 방식으로 학교 시스템에 접근할 수 있도록 지원합니다.

### 주요 기능

- **SSO 로그인**: 명지대학교 통합 로그인 시스템을 통한 인증
- **학생카드 조회**: 학번, 이름, 학과, 학적상태 등 기본 정보 조회
- **학적변동내역 조회**: 학적 변동 이력 조회
- **다양한 서비스 지원**: LMS, 포털, MSI, MyiCAP, 도서관 등

### 활용 사례

- 개인 학사 관리 자동화
- 학생 정보 기반 애플리케이션 개발
- 학교 시스템 연동 봇 제작

---

## 2. 사용법

### 설치

```bash
pip install mju-univ-auth
```

### 기본 사용법

#### 학생카드 정보 조회

```python
from mju_univ_auth import StudentCard

# 학번과 비밀번호로 학생카드 정보 조회
student_card = StudentCard.fetch(
    user_id="학번",
    user_pw="비밀번호"
)

# 정보 확인
print(f"이름: {student_card.name_korean}")
print(f"학번: {student_card.student_id}")
print(f"학과: {student_card.department}")
print(f"학년: {student_card.grade}")
print(f"학적상태: {student_card.status}")

# 딕셔너리로 변환
data = student_card.to_dict()
```

#### 학적변동내역 조회

```python
from mju_univ_auth import StudentChangeLog

# 학적변동내역 조회
change_log = StudentChangeLog.fetch(
    user_id="학번",
    user_pw="비밀번호"
)

# 정보 확인
print(f"학번: {change_log.student_id}")
print(f"이름: {change_log.name}")
print(f"학적상태: {change_log.status}")
print(f"이수학기: {change_log.completed_semesters}")

# 딕셔너리로 변환
data = change_log.to_dict()
```

#### SSO 로그인 (저수준 API)

다양한 명지대학교 서비스에 직접 로그인할 수 있습니다.

```python
from mju_univ_auth.sso import MJUSSOLogin

# SSO 로그인 객체 생성
sso = MJUSSOLogin(user_id="학번", user_pw="비밀번호")

# 서비스별 로그인 (session 객체 반환)
session = sso.login(service='msi')      # My iWeb
session = sso.login(service='lms')      # e-Class (LMS)
session = sso.login(service='portal')   # 통합정보시스템
session = sso.login(service='myicap')   # MyiCAP
session = sso.login(service='library')  # 도서관

# 반환된 session으로 추가 요청 가능
response = session.get("https://msi.mju.ac.kr/...")
```

### 예외 처리

```python
from mju_univ_auth import (
    StudentCard,
    MyIWebError,
    InvalidCredentialsError,
    NetworkError,
    SessionExpiredError
)

try:
    student_card = StudentCard.fetch(user_id="학번", user_pw="비밀번호")
except InvalidCredentialsError:
    print("아이디 또는 비밀번호가 올바르지 않습니다.")
except NetworkError:
    print("네트워크 연결에 실패했습니다.")
except SessionExpiredError:
    print("세션이 만료되었습니다.")
except MyIWebError as e:
    print(f"오류 발생: {e}")
```

### 환경 변수 사용 (권장)

보안을 위해 환경 변수나 `.env` 파일을 사용하는 것을 권장합니다.

```python
import os
from dotenv import load_dotenv
from mju_univ_auth import StudentCard

load_dotenv()

student_card = StudentCard.fetch(
    user_id=os.getenv('MJU_ID'),
    user_pw=os.getenv('MJU_PW')
)
```

`.env` 파일 예시:
```
MJU_ID=학번
MJU_PW=비밀번호
```

### 상세 로그 출력

디버깅을 위해 상세 로그를 활성화할 수 있습니다.

```python
student_card = StudentCard.fetch(
    user_id="학번",
    user_pw="비밀번호",
    verbose=True  # 상세 로그 출력
)
```

---

## 3. 이종 언어를 위한 서버 요청

<!-- TODO: 내용 추가 예정 -->

## 4. 기술적 설명

<!-- TODO: 기술적 상세 내용 추가 예정 -->

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 주의사항

- 이 라이브러리는 비공식 라이브러리입니다.
- 명지대학교 학생만 사용할 수 있습니다.
- 개인 정보 보호를 위해 비밀번호를 코드에 직접 작성하지 마세요.
- 과도한 요청은 서버에 부담을 줄 수 있으니 적절히 사용해주세요.
