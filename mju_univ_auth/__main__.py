"""
명지대학교 My iWeb 모듈 실행 엔트리포인트 (CLI)
==============================================
`python -m mju_univ_auth` 명령으로 실행됩니다.
"""

import os
import json

from dotenv import load_dotenv

from .facade import MjuUnivAuth
from .exceptions import MjuUnivAuthError
from .utils import Colors, get_logger


def main():
    """CLI 메인 함수"""
    logger = get_logger(verbose=True)
    
    # .env 파일 로드
    load_dotenv()
    
    # 환경변수에서 인증 정보 로드
    user_id = os.getenv('MJU_ID', '').strip()
    user_pw = os.getenv('MJU_PW', '').strip()
    
    # CLI 배너 출력
    banner = (
        f"\n{Colors.BOLD}{Colors.HEADER}\n"
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║           명지대학교 mju-univ-auth 정보 조회 프로그램                   ║\n"
        "║                                                                      ║\n"
        "║  이 프로그램은 MyiWeb에 로그인하여 학생 정보를 조회합니다.                ║\n"
        "║  - 지원 기능: 학생카드, 학적변동내역                                     ║\n"
        "║                                                                      ║\n"
        "║  https://github.com/shinnyeonki/mju-univ-auth                        ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝\n"
        f"{Colors.END}\n"
    )
    print(banner)
    
    if not user_id or not user_pw:
        logger.error(".env 파일에서 MJU_ID, MJU_PW를 찾을 수 없습니다.")
        print("\n환경변수 설정 방법:")
        print("  export MJU_ID=학번")
        print("  export MJU_PW=비밀번호")
        print("\n또는 .env 파일 형식:")
        print("  MJU_ID=학번")
        print("  MJU_PW=비밀번호")
        return
    
    try:
        # MjuUnivAuth 인스턴스 생성 (verbose 모드)
        auth = MjuUnivAuth(user_id=user_id, user_pw=user_pw, verbose=True)
        
        # 1. 학생카드 정보 조회
        logger.section("학생카드 정보 조회")
        student_card = auth.get_student_card(print_summary=True)
        logger.success("학생카드 정보 조회 완료!")
        
        # JSON 형태로 출력
        print(f"\n{Colors.BOLD}[학생카드 JSON]{Colors.END}")
        print(json.dumps(student_card.to_dict(), ensure_ascii=False, indent=2))

        # 2. 학적변동내역 정보 조회
        logger.section("학적변동내역 조회")
        changelog = auth.get_student_changelog(print_summary=True)
        logger.success("학적변동내역 조회 완료!")

        # JSON 형태로 출력
        print(f"\n{Colors.BOLD}[학적변동내역 JSON]{Colors.END}")
        print(json.dumps(changelog.to_dict(), ensure_ascii=False, indent=2))
        
    except MjuUnivAuthError as e:
        logger.section("실패")
        logger.error(str(e))


if __name__ == "__main__":
    main()
