"""
MjuUnivAuth Facade
==================
사용자 친화적 API를 제공하는 메인 클래스입니다.
"""

from typing import Optional

from .infrastructure.http_client import HTTPClient
from .services.sso_service import SSOService
from .services.student_card_service import StudentCardService
from .services.student_changelog_service import StudentChangeLogService
from .domain.student_card import StudentCard
from .domain.student_changelog import StudentChangeLog
from .utils import Logger, get_logger


class MjuUnivAuth:
    """
    명지대학교 인증 및 정보 조회를 위한 메인 클래스
    
    사용 예시:
    ```python
    from mju_univ_auth import MjuUnivAuth
    
    auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
    
    # 학생카드 정보 조회
    student_card = auth.get_student_card()
    print(student_card.name_korean)
    
    # 학적변동내역 조회
    changelog = auth.get_student_changelog()
    print(changelog.status)
    ```
    """
    
    def __init__(
        self,
        user_id: str,
        user_pw: str,
        verbose: bool = False,
    ):
        """
        Args:
            user_id: 학번/교번
            user_pw: 비밀번호
            verbose: 상세 로그 출력 여부
        """
        self.user_id = user_id
        self.user_pw = user_pw
        self.verbose = verbose
        
        self._logger: Logger = get_logger(verbose)
        self._http_client: Optional[HTTPClient] = None
        self._logged_in_service: Optional[str] = None
    
    def _ensure_login(self, service: str = 'msi') -> HTTPClient:
        """필요 시 로그인 수행"""
        # 이미 해당 서비스에 로그인된 경우 기존 클라이언트 재사용
        if self._http_client and self._logged_in_service == service:
            return self._http_client
        
        # 새로운 로그인 수행
        sso = SSOService(
            user_id=self.user_id,
            user_pw=self.user_pw,
            http_client=HTTPClient(),  # 새 HTTP 클라이언트
            logger=self._logger,
        )
        
        self._http_client = sso.login(service=service)
        self._logged_in_service = service
        
        return self._http_client
    
    def get_student_card(self, print_summary: bool = False) -> StudentCard:
        """
        학생카드 정보를 조회합니다.
        
        Args:
            print_summary: 조회 결과 요약 출력 여부
        
        Returns:
            StudentCard: 학생카드 정보
        
        Raises:
            InvalidCredentialsError: 로그인 실패
            NetworkError: 네트워크 오류
            PageParsingError: 페이지 파싱 실패
        """
        if self.verbose:
            self._logger.section("mju-univ-auth: 학생카드 조회")
        
        http_client = self._ensure_login(service='msi')
        
        service = StudentCardService(
            http_client=http_client,
            user_pw=self.user_pw,
            logger=self._logger,
        )
        
        student_card = service.fetch()
        
        if print_summary:
            student_card.print_summary()
        
        return student_card
    
    def get_student_changelog(self, print_summary: bool = False) -> StudentChangeLog:
        """
        학적변동내역을 조회합니다.
        
        Args:
            print_summary: 조회 결과 요약 출력 여부
        
        Returns:
            StudentChangeLog: 학적변동내역 정보
        
        Raises:
            InvalidCredentialsError: 로그인 실패
            NetworkError: 네트워크 오류
            PageParsingError: 페이지 파싱 실패
        """
        if self.verbose:
            self._logger.section("mju-univ-auth: 학적변동내역 조회")
        
        http_client = self._ensure_login(service='msi')
        
        service = StudentChangeLogService(
            http_client=http_client,
            logger=self._logger,
        )
        
        changelog = service.fetch()
        
        if print_summary:
            changelog.print_summary()
        
        return changelog
    
    def login(self, service: str = 'msi') -> 'MjuUnivAuth':
        """
        명시적 로그인 수행 (체이닝 지원)
        
        Args:
            service: 로그인할 서비스 ('lms', 'portal', 'library', 'msi', 'myicap')
        
        Returns:
            self (메서드 체이닝 지원)
        """
        self._ensure_login(service=service)
        return self
    
    def test_session(self, service: str = 'msi') -> bool:
        """
        현재 세션의 유효성을 테스트합니다.
        
        Args:
            service: 테스트할 서비스
        
        Returns:
            bool: 세션 유효 여부
        """
        if not self._http_client:
            return False
        
        sso = SSOService(
            user_id=self.user_id,
            user_pw=self.user_pw,
            http_client=self._http_client,
            logger=self._logger,
        )
        
        return sso.test_session(service=service)
    
    @property
    def is_logged_in(self) -> bool:
        """로그인 상태 확인"""
        return self._http_client is not None and self._logged_in_service is not None
