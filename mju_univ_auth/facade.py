"""
MjuUnivAuth Facade
==================
사용자 친화적 고수준 API를 제공하는 메인 클래스입니다.
"""

from typing import Optional
import logging
import requests

from .authenticator.standard_authenticator import StandardAuthenticator
from .fetcher.student_basicinfo_fetcher import StudentBasicInfoFetcher
from .fetcher.student_card_fetcher import StudentCardFetcher
from .fetcher.student_changelog_fetcher import StudentChangeLogFetcher
from .domain.student_basicinfo import StudentBasicInfo
from .domain.student_card import StudentCard
from .domain.student_changelog import StudentChangeLog
from .results import MjuUnivAuthResult, ErrorCode

logger = logging.getLogger(__name__)


class MjuUnivAuth:
    """
    명지대학교 통합 인증/정보 조회 Facade
    
    - "하나의 인스턴스는 하나의 성공적인 세션만 책임진다" 원칙을 따릅니다.
    - 복잡한 내부 로직(Session 관리, Fetcher 인스턴스화 등)을 숨깁니다.

    사용 예시:
    ```python
    from mju_univ_auth import MjuUnivAuth

    auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
    
    # 1. 로그인 수행
    login_result = auth.login("msi")
    if not login_result.success:
        print(f"로그인 실패: {login_result.error_message}")
        return

    # 2. 로그인 상태 확인 및 세션 사용
    if auth.is_logged_in():
        print(f"로그인 성공! 서비스: {auth.service}")
        # auth.session을 통해 requests.Session 객체 직접 사용 가능
        # print(auth.session.cookies)

    # 3. 정보 조회
    card_result = auth.get_student_card()
    if card_result.success:
        print(f"이름: {card_result.data.student_profile.name_korean}")
    else:
        print(f"학생증 조회 실패: {card_result.error_message}")
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
        self._user_id = user_id
        self._user_pw = user_pw
        self._verbose = verbose
        
        self._service: Optional[str] = None
        self._login_result: Optional[MjuUnivAuthResult] = None

    def login(self, service: str = 'msi') -> 'MjuUnivAuth':
        """
        로그인을 수행합니다.
        성공 시 self를 반환하여 체이닝을 지원합니다.
        실패 시 self를 반환하지만 내부 플래그를 설정하여 이후 메서드 호출 시 실패를 반환합니다.
        "하나의 인스턴스, 하나의 성공적인 세션" 원칙에 따라, 이미 로그인된 경우 실패 처리됩니다.
        평균 응답 시간은 약 800ms 내외입니다.
        
        Args:
            service: 로그인할 서비스 ('main', 'msi', 'lms', 'portal', 'myicap', 'intern', 'ipp', 'ucheck')
        
        Returns:
            MjuUnivAuth: self (체이닝 지원)
        
        Raises:
            ValueError: 이미 로그인된 경우
        """

        authenticator = StandardAuthenticator(
            user_id=self._user_id,
            user_pw=self._user_pw,
            verbose=self._verbose
        )
        self._login_result = authenticator.login(service)
        
        if self._login_result.success:
            self._service = service
        else:
            self._service = None
        return self

    def is_logged_in(self, service: str = 'msi') -> bool:
        """
        현재 세션이 유효한지 확인합니다.
        내부적으로 네트워크 요청을 보내 서버의 세션 상태를 확인합니다.
        평균 응답 시간은 약 300ms 내외입니다.
        
        Args:
            service: 유효성을 확인할 서비스.
        
        Returns:
            bool: 세션 유효 여부
        """
        if self._login_result is None or not self._login_result.success:
            return False
        
        # 요청받은 대로 Authenticator를 생성하여 세션 유효성 검사
        authenticator = StandardAuthenticator(
            user_id=self._user_id,
            user_pw=self._user_pw,
            verbose=self._verbose
        )
        authenticator._session = self._login_result.data  # 세션 설정
        return authenticator.is_session_valid(service)

    @property
    def session(self) -> Optional[requests.Session]:
        """
        현재 로그인된 `requests.Session` 객체를 반환합니다.
        로그인되지 않은 경우 `None`을 반환합니다.
        """
        return self._login_result.data if self._login_result and self._login_result.success else None

    @property
    def service(self) -> Optional[str]:
        """
        로그인에 성공한 서비스의 이름을 반환합니다.
        로그인되지 않은 경우 `None`을 반환합니다.
        """
        return self._service

    def get_session(self) -> MjuUnivAuthResult[requests.Session]:
        """
        현재 로그인된 세션을 반환합니다.
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 세션 객체
        """
        if self._login_result is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                error_message="세션이 없습니다."
            )
        return self._login_result

    # =================================================================
    # 데이터 조회 메서드 (고수준 API)
    # =================================================================

    def get_student_basicinfo(self) -> MjuUnivAuthResult[StudentBasicInfo]:
        """
        학생 기본 정보(대시보드 요약)를 조회합니다.
        MSI 서비스 로그인이 필요합니다.

        Returns:
            MjuUnivAuthResult[StudentBasicInfo]: 학생 기본 정보 조회 결과
        """
        if self._verbose:
            logger.info("===== mju-univ-auth: 학생 기본 정보 조회 =====")
        
        if self._login_result is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                error_message="세션이 없습니다."
            )
        
        if not self._login_result.success:
            return self._login_result
        
        if self._service != 'msi':
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.INVALID_SERVICE_USAGE_ERROR,
                error_message="MSI 서비스로 로그인된 세션이 아닙니다. 학생 기본 정보는 MSI 서비스 로그인이 필요합니다."
            )

        fetcher = StudentBasicInfoFetcher(
            session=self._login_result.data,
            verbose=self._verbose,
        )
        return fetcher.fetch()

    def get_student_card(self) -> MjuUnivAuthResult[StudentCard]:
        """
        학생카드 정보를 조회합니다.
        MSI 서비스 로그인이 필요하며, 내부적으로 2차 인증을 수행합니다.
        이 메서드를 호출하기 전에 반드시 세션이 msi 서비스로 로그인되어 있어야 합니다.

        Returns:
            MjuUnivAuthResult[StudentCard]: 학생카드 정보 조회 결과
        """
        if self._verbose:
            logger.info("===== mju-univ-auth: 학생카드 조회 =====")
        
        if self._login_result is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                error_message="세션이 없습니다."
            )
        
        if not self._login_result.success:
            return self._login_result
        
        if self._service != 'msi':
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.INVALID_SERVICE_USAGE_ERROR,
                error_message="MSI 서비스로 로그인된 세션이 아닙니다. 학생카드 정보는 MSI 서비스 로그인이 필요합니다."
            )

        fetcher = StudentCardFetcher(
            session=self._login_result.data,
            user_pw=self._user_pw,
            verbose=self._verbose,
        )
        return fetcher.fetch()

    def get_student_changelog(self) -> MjuUnivAuthResult[StudentChangeLog]:
        """
        학적변동내역을 조회합니다.
        MSI 서비스 로그인이 필요합니다.
        이 메서드를 호출하기 전에 반드시 세션이 msi 서비스로 로그인되어 있어야 합니다.
    
        Returns:
            MjuUnivAuthResult[StudentChangeLog]: 학적변동내역 정보 조회 결과
        """
        if self._verbose:
            logger.info("===== mju-univ-auth: 학적변동내역 조회 =====")
    
        if self._login_result is None:
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.SESSION_NOT_EXIST_ERROR,
                error_message="세션이 없습니다."
            )
    
        if not self._login_result.success:
            return self._login_result
    
        if self._service != 'msi':
            return MjuUnivAuthResult(
                request_succeeded=False,
                error_code=ErrorCode.INVALID_SERVICE_USAGE_ERROR,
                error_message="MSI 서비스로 로그인된 세션이 아닙니다. 학적변동내역 정보는 MSI 서비스 로그인이 필요합니다."
            )
    
        fetcher = StudentChangeLogFetcher(
            session=self._login_result.data,
            verbose=self._verbose,
        )
        return fetcher.fetch()
