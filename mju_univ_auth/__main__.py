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
from .sugang_authenticator import SugangAuthenticator
from .sugang_list_fetcher import SugangListFetcher
from .domain.lecture_search_request import LectureSearchRequest
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

# def sugang_list():

# 수강신청 강의 검색 카테고리 목록
SUGANG_CATEGORIES = {
    "자연캠퍼스 공통교양 성서와인간이해": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "01",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 공통교양 채플": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "02",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 공통교양 영어": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "03",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 공통교양 영어회화": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "04",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 공통교양 기타교양필수": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "05",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 핵심교양 핵심교양과목": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "06",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 기독교의이해와삶": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "19",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 인문과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "11",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 문화와예술": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "12",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 사회과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "13",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 자연과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "14",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 공학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "15",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 건강과생활": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "16",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 외국어": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "17",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 컴퓨터": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "18",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 일반교양 특별주제명사초대강좌": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "자연캠퍼스 교직 교직": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "10000",
        "displayDiv": "30",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 스마트시스템공과대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15400",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 화공신소재공학부 화학공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15411",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 화공신소재공학부 신소재공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15412",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 스마트인프라공학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15420",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 스마트인프라공학부 환경시스템공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15421",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 스마트인프라공학부 건설환경공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15422",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 스마트인프라공학부 스마트모빌리티공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15423",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스마트시스템공과대학) 기계시스템공학부 기계공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15431",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 반도체·ICT대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15600",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 컴퓨터정보통신공학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15610",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 컴퓨터정보통신공학부 컴퓨터공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15611",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 컴퓨터정보통신공학부 정보통신공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15612",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 전기전자공학부 전기공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15621",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 전기전자공학부 전자공학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15622",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 산업경영공학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15630",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 반도체공학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15640",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(반도체·ICT대학) 반도체시스템공학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15650",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 화학·생명과학대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15800",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 물리학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15808",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 수학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15809",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 화학·에너지융합학부 화학나노학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15811",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 융합바이오학부 식품영양학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15821",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(화학·생명과학대학) 융합바이오학부 시스템생명과학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "15822",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 바둑학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17609",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 디자인학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17610",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 스포츠학부(체육학전공, 스포츠산업학전공)": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17621",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 스포츠학부 스포츠지도학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17622",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 아트앤멀티미디어음악학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17630",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 아트앤멀티미디어음악학부 건반음악전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17631",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 아트앤멀티미디어음악학부 보컬뮤직전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17632",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 아트앤멀티미디어음악학부 작곡전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17633",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 공연예술학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17640",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 공연예술학부 연극·영화전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17641",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(스포츠·예술대학) 공연예술학부 뮤지컬공연전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "17642",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(건축대학) 건축대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "18000",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(건축대학) 건축학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "18030",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(건축대학) 건축학부 건축학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "18031",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(건축대학) 건축학부 전통건축학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "18032",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(건축대학) 공간디자인학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "18040",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(융합전공) 융합전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "19000",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(융합전공) 제약바이오": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "19034",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(융합전공) 멀티미디어콘텐츠크리에이션": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "10",
        "deptCd": "19038",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 공통교양 성서와인간이해": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "01",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 공통교양 채플": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "02",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 공통교양 영어": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "03",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 공통교양 영어회화": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "04",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 공통교양 기타교양필수": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "05",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 핵심교양 핵심교양과목": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "06",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 기독교의이해와삶": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "19",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 인문과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "11",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 문화와예술": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "12",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 사회과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "13",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 자연과학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "14",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 공학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "15",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 건강과생활": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "16",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 외국어": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "17",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 컴퓨터": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "18",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 일반교양 특별주제명사초대강좌": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "인문캠퍼스 교직 교직": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "20000",
        "displayDiv": "30",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 인문대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14000",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 사학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14190",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 미술사학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14212",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 철학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14240",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 문예창작학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14250",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 아시아·중동어문학부 중어중문학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14411",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 아시아·중동어문학부 일어일문학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14412",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 아시아·중동어문학부 아랍지역학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14413",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 아시아·중동어문학부 글로벌한국어학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14414",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 인문콘텐츠학부 국어국문학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14421",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 인문콘텐츠학부 영어영문학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14422",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 인문콘텐츠학부 미술사·역사학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14423",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인문대학) 인문콘텐츠학부 문헌정보학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14424",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미디어·휴먼라이프대학) 미디어·휴먼라이프대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14600",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미디어·휴먼라이프대학) 청소년지도·아동학부 청소년지도학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14611",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미디어·휴먼라이프대학) 청소년지도·아동학부 아동학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14612",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미디어·휴먼라이프대학) 디지털미디어학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "14620",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 사회과학대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16400",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 공공인재학부 행정학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16471",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 공공인재학부 정치외교학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16472",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 경상·통계학부 경제학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16481",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 경상·통계학부 응용통계학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16482",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 경상·통계학부 국제통상학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16483",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(사회과학대학) 법학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16490",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(경영대학) 경영대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16600",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(경영대학) 경영정보학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16640",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(경영대학) 국제통상학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16650",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(경영대학) 경영학부 경영학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16671",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(경영대학) 경영학부 글로벌비즈니스학전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "16672",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 미래융합대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17200",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 뮤직콘텐츠학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17205",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 사회복지학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17220",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 부동산학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17230",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 아동심리상담학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17235",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 물류유통경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17250",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 융합예술실용음악학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17255",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 법무행정학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17260",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 복지경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17265",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 심리치료학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17270",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 복지상담학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17275",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 미래융합경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17280",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 유통산업경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17290",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 만화애니콘텐츠학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17295",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 멀티디자인학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17310",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 스포츠산업경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17320",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 융합디자인학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17330",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 복지상담경영학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17350",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 미용예술학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17355",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 웹툰콘텐츠학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17360",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 회계세무학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17362",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 미디어앤아트테크놀로지학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17365",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(미래융합대학) 영유아교육상담학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "17367",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인공지능·소프트웨어융합대학) 인공지능·소프트웨어융합대학": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "18600",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인공지능·소프트웨어융합대학) 디지털콘텐츠디자인학과": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "18610",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인공지능·소프트웨어융합대학) 융합소프트웨어학부": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "18620",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인공지능·소프트웨어융합대학) 융합소프트웨어학부 응용소프트웨어전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "18621",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(인공지능·소프트웨어융합대학) 융합소프트웨어학부 데이터사이언스전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "18622",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
    "(융합전공) 융합예술학융합전공": {
        "courseCls": "",
        "curiNm": "",
        "campusDiv": "20",
        "deptCd": "19036",
        "displayDiv": "27",
        "searchType": "1",
        "excludeDay": ""
    },
}


def test_sugang_list(user_id: str, user_pw: str, category_name: str = None) -> bool:
    """
    수강신청 강의 목록 조회 테스트
    
    Args:
        user_id: 학번
        user_pw: 비밀번호
        category_name: 조회할 카테고리 이름 (None이면 기본값 사용)
    
    Returns:
        bool: 테스트 성공 여부
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 5. 수강신청 강의 목록 조회 테스트")
    print(f"{'='*70}{Colors.END}\n")
    
    # 5-1. 수강신청 시스템 로그인
    print(f"{Colors.BOLD}{Colors.BLUE}[Step 5-1] 수강신청 시스템 로그인{Colors.END}")
    
    auth = SugangAuthenticator(user_id=user_id, user_pw=user_pw, verbose=True)
    login_result = auth.authenticate()
    
    if not login_result.success:
        print(f"{Colors.RED}✗ 수강신청 로그인 실패: {login_result.error_message}{Colors.END}")
        return False
    
    print(f"{Colors.GREEN}✓ 수강신청 로그인 성공!{Colors.END}")
    
    # CSRF 정보 획득
    csrf_header, csrf_token = auth.get_csrf_info()
    if not csrf_token:
        print(f"{Colors.RED}✗ CSRF 토큰을 획득하지 못했습니다.{Colors.END}")
        return False
    
    print(f"  {Colors.CYAN}CSRF Header:{Colors.END} {csrf_header}")
    print(f"  {Colors.CYAN}CSRF Token:{Colors.END} {csrf_token[:20]}...")
    
    # 5-2. SugangListFetcher로 강의 검색
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step 5-2] 강의 목록 조회{Colors.END}")
    
    fetcher = SugangListFetcher(
        session=login_result.data,
        csrf_token=csrf_token,
        csrf_header=csrf_header,
        verbose=True
    )
    
    # 검색할 카테고리 선택
    if category_name and category_name in SUGANG_CATEGORIES:
        selected_category = category_name
    else:
        # 기본값: 컴퓨터공학전공
        selected_category = "자연캠퍼스 공통교양 성서와인간이해"
    
    category_data = SUGANG_CATEGORIES[selected_category]
    print(f"  {Colors.CYAN}검색 카테고리:{Colors.END} {selected_category}")
    
    # LectureSearchRequest 생성
    request = LectureSearchRequest.from_dict(category_data)
    
    # 강의 검색
    search_result = fetcher.search(request)
    
    if not search_result.success:
        print(f"{Colors.RED}✗ 강의 검색 실패: {search_result.error_message}{Colors.END}")
        return False
    
    # 결과 출력
    lecture_result = search_result.data
    print(f"{Colors.GREEN}✓ 강의 검색 성공!{Colors.END}")
    print(f"  {Colors.CYAN}검색된 강의 수:{Colors.END} {lecture_result.total_count}개")
    
    # 처음 5개 강의 정보 출력
    print(f"\n{Colors.BOLD}[검색된 강의 목록 (최대 5개)]{Colors.END}")
    for i, lecture in enumerate(lecture_result.lectures[:5], 1):
        print(f"\n  {Colors.CYAN}[{i}] {lecture.curi_nm}{Colors.END}")
        print(f"      강좌번호: {lecture.course_cls}")
        print(f"      학점: {lecture.credit}")
        print(f"      교수: {lecture.prof_nm}")
        print(f"      시간: {lecture.lec_time_room}")
        print(f"      정원: {lecture.limit_cnt}, 신청: {lecture.sugang_cnt}")
    
    if lecture_result.total_count > 5:
        print(f"\n  ... 외 {lecture_result.total_count - 5}개 강의")
    
    # JSON으로도 출력
    print(f"\n{Colors.BOLD}[첫 번째 강의 상세 JSON]{Colors.END}")
    if lecture_result.lectures:
        print(json.dumps(lecture_result.lectures[0].to_dict(), ensure_ascii=False, indent=2))
    
    return True


def list_sugang_categories():
    """
    사용 가능한 수강신청 카테고리 목록 출력
    """
    print(f"\n{Colors.HEADER}{'='*70}")
    print(" 사용 가능한 수강신청 카테고리 목록")
    print(f"{'='*70}{Colors.END}\n")
    
    # 캠퍼스별로 분류
    yongin_categories = []
    seoul_categories = []
    dept_categories = []
    
    for name, data in SUGANG_CATEGORIES.items():
        if name.startswith("자연캠퍼스"):
            yongin_categories.append(name)
        elif name.startswith("인문캠퍼스"):
            seoul_categories.append(name)
        else:
            dept_categories.append(name)
    
    print(f"{Colors.BOLD}[자연캠퍼스 (용인) 교양]{Colors.END}")
    for cat in yongin_categories:
        print(f"  - {cat}")
    
    print(f"\n{Colors.BOLD}[인문캠퍼스 (서울) 교양]{Colors.END}")
    for cat in seoul_categories:
        print(f"  - {cat}")
    
    print(f"\n{Colors.BOLD}[학과/전공]{Colors.END}")
    for cat in dept_categories:
        print(f"  - {cat}")
    
    print(f"\n총 {len(SUGANG_CATEGORIES)}개 카테고리")
    

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
    # service_results = test_all_services_login(user_id, user_pw)
    # fetcher_ok = test_fetchers_with_session(user_id, user_pw)
    # chaining_ok = test_chaining_api(user_id, user_pw)
    
    # 수강신청 강의 목록 테스트
    test_sugang_list(user_id, user_pw)
    
    # 결과 요약
    # print_summary(high_level_ok, service_results, fetcher_ok, chaining_ok)


if __name__ == "__main__":
    main()
