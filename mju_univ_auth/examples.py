"""
사용 예제
========
myiweb 모듈을 사용하여 학생 정보를 조회하는 예제

사용법:
1. .env 파일에 MJU_ID와 MJU_PW 설정
2. python -m myiweb.examples 실행
"""

import os
import sys
import json
from dotenv import load_dotenv

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from myiweb import StudentCard, StudentChangeLog, MyIWebError
from myiweb.sso import MJUSSOLogin
from myiweb.utils import log_info, log_success, log_error


def example_high_level():
    """
    고수준(High-level) API 사용 예제
    - 가장 권장되는 사용법입니다.
    """
    print("\n=== 고수준 API 예제 (가장 권장) ===\n")
    load_dotenv()
    
    user_id = os.getenv('MJU_ID')
    user_pw = os.getenv('MJU_PW')

    if not user_id or not user_pw:
        log_error("Skipping high-level example: .env 파일에 MJU_ID와 MJU_PW를 설정해주세요.")
        return
    
    try:
        # 1. 학생카드 정보 조회 (로그인부터 모든 과정 포함)
        log_info("API Call", "StudentCard.fetch(user_id, user_pw) 호출...")
        student_card = StudentCard.fetch(user_id, user_pw, verbose=False)
        log_success("학생카드 정보 조회 성공!")
        print("\n--- 학생카드 JSON 출력 ---")
        print(json.dumps(student_card.to_dict(), ensure_ascii=False, indent=2))
        
        # 2. 학적변동내역 정보 조회
        log_info("API Call", "StudentChangeLog.fetch(user_id, user_pw) 호출...")
        change_log = StudentChangeLog.fetch(user_id, user_pw, verbose=False)
        log_success("학적변동내역 정보 조회 성공!")
        print("\n--- 학적변동내역 JSON 출력 ---")
        print(json.dumps(change_log.to_dict(), ensure_ascii=False, indent=2))
        print("---------------------------\n")

    except MyIWebError as e:
        log_error(f"고수준 API 테스트 실패: {e}")


def example_services():
    """다양한 서비스 로그인 예제"""
    print("\n=== 다양한 서비스 로그인 테스트 예제 ===\n")
    load_dotenv()
    
    user_id = os.getenv('MJU_ID')
    user_pw = os.getenv('MJU_PW')

    if not user_id or not user_pw:
        log_error("Skipping services example: .env 파일에 MJU_ID와 MJU_PW를 설정해주세요.")
        return
    
    # 지원되는 서비스 목록
    services = ['lms', 'portal', 'msi', 'myicap', 'library']
    
    for service in services:
        try:
            sso = MJUSSOLogin(user_id, user_pw, verbose=False)
            sso.login(service=service)
            log_success(f"✓ {service} 로그인 성공")
        except MyIWebError as e:
            log_error(f"✗ {service} 로그인 실패: {e}")


if __name__ == "__main__":
    example_high_level()
    example_services()

