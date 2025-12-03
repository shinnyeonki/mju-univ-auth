"""
명지대학교 My iWeb 모듈 실행 엔트리포인트 (CLI)
==============================================
`python -m mju_univ_auth` 명령으로 실행됩니다.

테스트 항목:
1. 고수준 API (MjuUnivAuth) 테스트
   - 학생카드 조회
   - 학적변동내역 조회

2. 저수준 API (Authenticator) 테스트
   - 모든 서비스 로그인 테스트 (main, msi, lms, portal, myicap, intern, ipp, ucheck)

3. Fetcher 직접 사용 테스트
   - StudentCardFetcher
   - StudentChangeLogFetcher
"""

import os
import json
import logging
from typing import List, Tuple

from dotenv import load_dotenv

from .facade import MjuUnivAuth
from .authenticator import Authenticator
from .student_card_fetcher import StudentCardFetcher
from .student_change_log_fetcher import StudentChangeLogFetcher
from .config import SERVICES

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


# ANSI 컬러 코드
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'



def print_banner():
    """CLI 배너 출력"""
    banner = (
        f"\n"
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║           명지대학교 mju-univ-auth 통합 테스트 프로그램                  ║\n"
        "║                                                                      ║\n"
        "║  이 프로그램은 모든 API를 테스트합니다.                                   ║\n"
        "║  - 고수준 API: MjuUnivAuth                                            ║\n"
        "║  - 저수준 API: Authenticator, Fetchers                                ║\n"
        "║                                                                      ║\n"
        "║  https://github.com/shinnyeonki/mju-univ-auth                        ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝\n"
        f"\n"
    )
    print(banner)


def test_high_level_api(user_id: str, user_pw: str) -> bool:
    """
    고수준 API (MjuUnivAuth) 테스트
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 1. 고수준 API (MjuUnivAuth) 테스트")
    print(f"{'='*70}{Colors.END}\n")
    
    auth = MjuUnivAuth(user_id=user_id, user_pw=user_pw, verbose=True)
    
    # 1-1. 학생카드 조회 (자동 로그인)
    print(f"{Colors.BOLD}{Colors.BLUE}[Step 1-1] 학생카드 조회 (자동 로그인){Colors.END}")
    card_result = auth.get_student_card()
    
    if card_result.success:
        student_card = card_result.data
        student_card.print_summary()
        print(f"{Colors.GREEN}✓ 학생카드 정보 조회 완료!{Colors.END}")
        print(f"\n{Colors.BOLD}[학생카드 JSON]{Colors.END}")
        print(json.dumps(student_card.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"{Colors.RED}✗ 학생카드 정보 조회 실패 (코드: {card_result.error_code}){Colors.END}")
        print(f"  {Colors.CYAN}에러 메시지:{Colors.END} {card_result.error_message}")
        return False
    
    # 1-2. 학적변동내역 조회 (이미 로그인된 세션 사용)
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 1-2] 학적변동내역 조회 (기존 세션 사용){Colors.END}")
    changelog_result = auth.get_student_changelog()
    
    if changelog_result.success:
        changelog = changelog_result.data
        changelog.print_summary()
        print(f"{Colors.GREEN}✓ 학적변동내역 조회 완료!{Colors.END}")
        print(f"\n{Colors.BOLD}[학적변동내역 JSON]{Colors.END}")
        print(json.dumps(changelog.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"{Colors.RED}✗ 학적변동내역 조회 실패 (코드: {changelog_result.error_code}){Colors.END}")
        print(f"  {Colors.CYAN}에러 메시지:{Colors.END} {changelog_result.error_message}")
        return False
    
    return True


def test_all_services_login(user_id: str, user_pw: str) -> List[Tuple[str, bool, str]]:
    """
    저수준 API (Authenticator) - 모든 서비스 로그인 테스트
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 2. 저수준 API (Authenticator) - 모든 서비스 로그인 테스트")
    print(f"{'='*70}{Colors.END}\n")
    
    results = []
    
    for service_name, service_config in SERVICES.items():
        print(f"{Colors.BOLD}{Colors.BLUE}[{service_name}] {service_config.name} 로그인 테스트{Colors.END}")
        
        authenticator = Authenticator(
            user_id=user_id,
            user_pw=user_pw,
            verbose=True
        )
        
        login_result = authenticator.login(service_name)
        
        if login_result.success:
            print(f"{Colors.GREEN}✓ {service_config.name} 로그인 성공!{Colors.END}")
            print(f"  {Colors.CYAN}세션:{Colors.END} Session ID: {id(login_result.data)}")
            results.append((service_name, True, "성공"))
        else:
            print(f"{Colors.RED}✗ {service_config.name} 로그인 실패{Colors.END}")
            print(f"  {Colors.CYAN}에러 코드:{Colors.END} {login_result.error_code}")
            print(f"  {Colors.CYAN}에러 메시지:{Colors.END} {login_result.error_message}")
            results.append((service_name, False, login_result.error_message))
        print()
    
    return results


def test_fetchers_with_session(user_id: str, user_pw: str) -> bool:
    """
    저수준 API - Fetcher 직접 사용 테스트 (MSI 세션 사용)
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 3. 저수준 API (Fetcher) - MSI 세션으로 직접 조회 테스트")
    print(f"{'='*70}{Colors.END}\n")
    
    # 3-1. MSI 로그인으로 세션 획득
    print(f"{Colors.BOLD}{Colors.BLUE}[Step 3-1] MSI 로그인으로 세션 획득{Colors.END}")
    authenticator = Authenticator(user_id=user_id, user_pw=user_pw, verbose=False)
    login_result = authenticator.login('msi')
    
    if not login_result.success:
        print(f"{Colors.RED}✗ MSI 로그인 실패 - Fetcher 테스트 불가{Colors.END}")
        return False
    
    session = login_result.data
    print(f"{Colors.GREEN}✓ MSI 세션 획득 완료{Colors.END}")
    
    # 3-2. StudentCardFetcher 직접 사용
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 3-2] StudentCardFetcher 직접 사용{Colors.END}")
    card_fetcher = StudentCardFetcher(session=session, user_pw=user_pw, verbose=False)
    card_result = card_fetcher.fetch()
    
    if card_result.success:
        print(f"{Colors.GREEN}✓ StudentCardFetcher 테스트 성공!{Colors.END}")
        print(f"  {Colors.CYAN}학번:{Colors.END} {card_result.data.student_id}")
        print(f"  {Colors.CYAN}이름:{Colors.END} {card_result.data.name_korean}")
    else:
        print(f"{Colors.RED}✗ StudentCardFetcher 테스트 실패: {card_result.error_message}{Colors.END}")
        return False
    
    # 3-3. StudentChangeLogFetcher 직접 사용
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 3-3] StudentChangeLogFetcher 직접 사용{Colors.END}")
    changelog_fetcher = StudentChangeLogFetcher(session=session, verbose=False)
    changelog_result = changelog_fetcher.fetch()
    
    if changelog_result.success:
        print(f"{Colors.GREEN}✓ StudentChangeLogFetcher 테스트 성공!{Colors.END}")
        print(f"  {Colors.CYAN}학번:{Colors.END} {changelog_result.data.student_id}")
        print(f"  {Colors.CYAN}학적상태:{Colors.END} {changelog_result.data.status}")
    else:
        print(f"{Colors.RED}✗ StudentChangeLogFetcher 테스트 실패: {changelog_result.error_message}{Colors.END}")
        return False
    
    return True


def test_chaining_api(user_id: str, user_pw: str) -> bool:
    """
    체이닝 API 테스트
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 4. 체이닝 API 테스트")
    print(f"{'='*70}{Colors.END}\n")
    
    # 4-1. 로그인 후 세션 받기
    print(f"{Colors.BOLD}{Colors.BLUE}[Step 4-1] 체이닝: login().get_session(){Colors.END}")
    auth = MjuUnivAuth(user_id=user_id, user_pw=user_pw, verbose=False)
    session_result = auth.login('msi').get_session()
    
    if session_result.success:
        print(f"{Colors.GREEN}✓ 체이닝으로 세션 획득 성공!{Colors.END}")
        print(f"  {Colors.CYAN}세션 ID:{Colors.END} {id(session_result.data)}")
    else:
        print(f"{Colors.RED}✗ 체이닝 세션 획득 실패: {session_result.error_message}{Colors.END}")
        return False
    
    # 4-2. 로그인 상태 확인
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 4-2] is_logged_in() 확인{Colors.END}")
    if auth.is_logged_in():
        print(f"{Colors.GREEN}✓ is_logged_in() = True{Colors.END}")
    else:
        print(f"{Colors.RED}✗ is_logged_in() = False (예상치 못한 결과){Colors.END}")
        return False
    
    # 4-3. 체이닝으로 바로 조회
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 4-3] 새 인스턴스로 login().get_student_changelog(){Colors.END}")
    auth2 = MjuUnivAuth(user_id=user_id, user_pw=user_pw, verbose=False)
    changelog_result = auth2.login('msi').get_student_changelog()
    
    if changelog_result.success:
        print(f"{Colors.GREEN}✓ 체이닝 조회 성공!{Colors.END}")
        print(f"  {Colors.CYAN}학번:{Colors.END} {changelog_result.data.student_id}")
    else:
        print(f"{Colors.RED}✗ 체이닝 조회 실패: {changelog_result.error_message}{Colors.END}")
        return False
    
    return True


def print_summary(high_level_ok: bool, service_results: List[Tuple[str, bool, str]], 
                  fetcher_ok: bool, chaining_ok: bool):
    """테스트 결과 요약 출력"""
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 테스트 결과 요약")
    print(f"{'='*70}{Colors.END}\n")
    
    print(f"{Colors.BOLD}[1. 고수준 API (MjuUnivAuth)]{Colors.END}")
    if high_level_ok:
        print(f"  {Colors.GREEN}✓ 성공{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ 실패{Colors.END}")
    
    print(f"\n{Colors.BOLD}[2. 모든 서비스 로그인]{Colors.END}")
    for service_name, success, msg in service_results:
        service_display = SERVICES[service_name].name
        if success:
            print(f"  {Colors.GREEN}✓ {service_name}: {service_display}{Colors.END}")
        else:
            print(f"  {Colors.RED}✗ {service_name}: {service_display} - {msg}{Colors.END}")
    
    print(f"\n{Colors.BOLD}[3. Fetcher 직접 사용]{Colors.END}")
    if fetcher_ok:
        print(f"  {Colors.GREEN}✓ 성공{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ 실패{Colors.END}")
    
    print(f"\n{Colors.BOLD}[4. 체이닝 API]{Colors.END}")
    if chaining_ok:
        print(f"  {Colors.GREEN}✓ 성공{Colors.END}")
    else:
        print(f"  {Colors.RED}✗ 실패{Colors.END}")
    
    # 전체 결과
    total_services = len(service_results)
    success_services = sum(1 for _, success, _ in service_results if success)
    all_passed = high_level_ok and fetcher_ok and chaining_ok and (success_services == total_services)
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 모든 테스트 통과!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ 일부 테스트 실패{Colors.END}")
        print(f"  서비스 로그인: {success_services}/{total_services}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")


def main():
    """CLI 메인 함수"""
    # .env 파일 로드
    load_dotenv()
    
    # 환경변수에서 인증 정보 로드
    user_id = os.getenv('MJU_ID', '').strip()
    user_pw = os.getenv('MJU_PW', '').strip()
    
    # 배너 출력
    print_banner()
    
    if not user_id or not user_pw:
        print(f"{Colors.RED}✗ .env 파일에서 MJU_ID, MJU_PW를 찾을 수 없습니다.{Colors.END}")
        print("\n환경변수 설정 방법:")
        print("  export MJU_ID=학번")
        print("  export MJU_PW=비밀번호")
        print("\n또는 .env 파일 형식:")
        print("  MJU_ID=학번")
        print("  MJU_PW=비밀번호")
        return
    
    # logging.getLogger().setLevel(logging.DEBUG)
    # 테스트 실행
    # high_level_ok = test_high_level_api(user_id, user_pw)
    service_results = test_all_services_login(user_id, user_pw)
    # fetcher_ok = test_fetchers_with_session(user_id, user_pw)
    # chaining_ok = test_chaining_api(user_id, user_pw)
    
    # 결과 요약
    # print_summary(high_level_ok, service_results, fetcher_ok, chaining_ok)


if __name__ == "__main__":
    main()
