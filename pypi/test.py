"""
mju-univ-auth 패키지 테스트
실제 PyPI에서 설치한 패키지를 테스트합니다.
"""

# 1. 패키지 import 테스트
print("=" * 50)
print("1. 패키지 Import 테스트")
print("=" * 50)

from mju_univ_auth import (
    StudentCard,
    StudentChangeLog,
    MyIWebError,
    NetworkError,
    PageParsingError,
    InvalidCredentialsError,
    SessionExpiredError
)
from mju_univ_auth.sso import MJUSSOLogin

print("✅ 모든 클래스 import 성공!")
print(f"  - StudentCard: {StudentCard}")
print(f"  - StudentChangeLog: {StudentChangeLog}")
print(f"  - MJUSSOLogin: {MJUSSOLogin}")
print(f"  - MyIWebError: {MyIWebError}")
print(f"  - NetworkError: {NetworkError}")
print(f"  - PageParsingError: {PageParsingError}")
print(f"  - InvalidCredentialsError: {InvalidCredentialsError}")
print(f"  - SessionExpiredError: {SessionExpiredError}")

# 2. 클래스 인스턴스 생성 테스트
print("\n" + "=" * 50)
print("2. 클래스 인스턴스 생성 테스트")
print("=" * 50)

# MJUSSOLogin 인스턴스 생성 (테스트용 더미 데이터)
sso = MJUSSOLogin(user_id="test_user", user_pw="test_password")
print(f"✅ MJUSSOLogin 인스턴스 생성 성공: {sso}")

# 3. 예외 클래스 테스트
print("\n" + "=" * 50)
print("3. 예외 클래스 테스트")
print("=" * 50)

try:
    raise InvalidCredentialsError("테스트 오류 메시지")
except InvalidCredentialsError as e:
    print(f"✅ InvalidCredentialsError 발생 및 캐치 성공: {e}")

try:
    raise NetworkError("네트워크 오류 테스트")
except MyIWebError as e:
    print(f"✅ NetworkError는 MyIWebError의 하위 클래스: {e}")

# 4. 모듈 정보 확인
print("\n" + "=" * 50)
print("4. 모듈 정보")
print("=" * 50)

import mju_univ_auth
print(f"패키지 위치: {mju_univ_auth.__file__}")
print(f"사용 가능한 항목: {mju_univ_auth.__all__}")

print("\n" + "=" * 50)
print("🎉 모든 테스트 통과!")
print("=" * 50)
