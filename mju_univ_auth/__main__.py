"""
명지대학교 My iWeb 모듈 실행 엔트리포인트 (CLI)
==============================================
`python -m mju-univ-auth` 명령으로 실행됩니다.
"""

import os
import json
from dotenv import load_dotenv

# 단순화된 API 임포트
from .student_card import StudentCard
from .student_changelog import StudentChangeLog
from .exceptions import MjuUnivAuthError
from .utils import Colors, log_section, log_success, log_error


def main():
    """CLI 메인 함수"""
    # 환경변수 로드
    load_dotenv()
    
    user_id = os.getenv('MJU_ID', '').strip()
    user_pw = os.getenv('MJU_PW', '').strip()
    
    # CLI 배너 출력
    banner = (
        f"\n{Colors.BOLD}{Colors.HEADER}\n"
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║           명지대학교 mju-univ-auth 정보 조회 프로그램 (mju-univ-auth)                  ║\n"
        "║                                                                      ║\n"
        "║  이 프로그램은 MyiWeb에 로그인하여 학생 정보를 조회합니다.                 ║\n"
        "║  - 지원 기능: 학생카드, 학적변동내역                                     ║\n"
        "║                                                                      ║\n"
        "║  https://github.com/shinnk/mju-sso-login                             ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝\n"
        f"{Colors.END}\n"
    )
    print(banner)
    
    if not user_id or not user_pw:
        log_error(".env 파일에서 MJU_ID, MJU_PW를 찾을 수 없습니다.")
        print("\n.env 파일 형식:")
        print("  MJU_ID=학번")
        print("  MJU_PW=비밀번호")
        return
    
    try:
        # 1. 학생카드 정보 조회 (로그인부터 모든 과정 포함)
        log_section("학생카드 정보 조회")
        student_card = StudentCard.fetch(user_id, user_pw, verbose=True)
        log_success("학생카드 정보 조회 완료!")
        
        # JSON 형태로 출력
        print(f"\n{Colors.BOLD}[학생카드 JSON]{Colors.END}")
        print(json.dumps(student_card.to_dict(), ensure_ascii=False, indent=2))

        # 2. 학적변동내역 정보 조회
        log_section("학적변동내역 조회")
        change_log = StudentChangeLog.fetch(user_id, user_pw, verbose=True)
        log_success("학적변동내역 조회 완료!")

        # JSON 형태로 출력
        print(f"\n{Colors.BOLD}[학적변동내역 JSON]{Colors.END}")
        print(json.dumps(change_log.to_dict(), ensure_ascii=False, indent=2))
        
        
    except MjuUnivAuthError as e:
        log_section("실패")
        log_error(str(e))


if __name__ == "__main__":
    main()