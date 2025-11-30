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

### 예외 처리

```python
from mju_univ_auth import (
    StudentCard,
    MjuUnivAuthError,
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
except MjuUnivAuthError as e:
    print(f"오류 발생: {e}")
```

### 환경 변수 사용 (권장)

테스트 시에 보안을 위해 환경 변수나 `.env` 파일을 사용하는 것을 권장합니다.

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

## 3. 이종 언어를 위한 API 서버

[서버 문서](api/README.md)  

## 4. 기술적 설명

<!-- TODO: 기술적 상세 내용 추가 예정 -->


2025년 11월 27일 부로 명지대학교의 여러 서비스 들이 1개의 로그인 방식(서버측 spring security 예상)으로 통합되었습니다  
기존 방식의 경우 어떤 서비스는 평문(userId passwrd), 암호화방식 등 여러 방식을 쓰고 있었지만 이제는 모든 로그인은 RSA+... 하이브리드 암호화 구조로 passwrd 는 암호화해서 전송됩니다(https 와는 무관한 중복 암호화)  
과거 전송 서버측 api가 현재 (2025/11/29) 아직 살아있지만 언제 막힐 지 몰라 해당 라이브러리를 만들었습니다
```
curl --location --request POST 'https://sso1.mju.ac.kr/mju/userCheck.do' \
--header 'id: USERID' \
--header 'passwd: PASSWORD'
```
위 코드는 현재(2025/11/29) 는 사용하지 않지만 동작하는 서버측 api 입니다.  

[기술적 설명 상세](doc/sso_login_process.md)  

---

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 주의사항
- 개인 정보 보호를 위해 비밀번호를 코드에 직접 작성하지 마세요. 외부에서 받아서 주입하여 이용(.env, 네트워크 요청)
