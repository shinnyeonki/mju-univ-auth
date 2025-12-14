"""
MjuUnivAuth Facade
==================
사용자 친화적 고수준 API를 제공하는 메인 클래스입니다.
"""

from typing import Optional
import logging
import requests

from .authenticator.standard_authenticator import StandardAuthenticator
from .fetcher.student_card_fetcher import StudentCardFetcher
from .fetcher.student_change_log_fetcher import StudentChangeLogFetcher
from .domain.student_card import StudentCard
from .domain.student_changelog import StudentChangeLog
from .results import MjuUnivAuthResult, ErrorCode

logger = logging.getLogger(__name__)


class MjuUnivAuth:
    """
    명지대학교 통합 인증/정보 조회 Facade
    
    - 복잡한 내부 로직(Session 관리, Fetcher 인스턴스화 등)을 숨김
    - 메서드 체이닝 지원

    사용 예시:
    ```python
    from mju_univ_auth import MjuUnivAuth, ErrorCode

    # 방법 1: 체이닝으로 로그인 후 조회
    auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
    result = auth.login("msi").get_student_card()
    
    # 방법 2: 세션만 받기
    auth = MjuUnivAuth(user_id="학번", user_pw="비밀번호")
    login_result = auth.login("lms").get_session()
    if login_result.success:
        session = login_result.data  # requests.Session 객체
    
    # 방법 3: 바로 조회 (내부적으로 자동 로그인)
    card_result = auth.get_student_card()
    if card_result.success:
        print(card_result.data.name_korean)
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
        
        self._session: Optional[requests.Session] = None
        self._login_result: Optional[MjuUnivAuthResult] = None

    def login(self, service: str = 'msi') -> 'MjuUnivAuth':
        """
        로그인을 수행하고 self를 반환하여 체이닝을 지원합니다.
        실패하더라도 예외를 발생시키지 않고, 내부 상태에 실패 결과를 저장합니다.
        
        Args:
            service: 로그인할 서비스 ('main', 'msi', 'lms', 'portal', 'myicap', 'intern', 'ipp', 'ucheck')
        
        Returns:
            self (메서드 체이닝 지원)
        """
        authenticator = StandardAuthenticator(
            user_id=self._user_id,
            user_pw=self._user_pw,
            verbose=self._verbose
        )
        result = authenticator.login(service)
        
        if result.success:
            self._session = result.data
            self._login_result = result
        else:
            self._session = None
            self._login_result = result
        
        return self

    def is_logged_in(self) -> bool:
        """현재 세션이 유효한지 확인"""
        return self._session is not None

    def get_session(self) -> MjuUnivAuthResult[requests.Session]:
        """
        현재 로그인된 세션을 반환합니다.
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 세션 결과
        """
        if self._session:
            return MjuUnivAuthResult(
                request_succeeded=True,
                credentials_valid=True,
                data=self._session
            )
        
        # 로그인 실패한 경우 실패 결과 반환. Use explicit `is not None` to avoid
        if self._login_result is not None: return self._login_result
        
        return MjuUnivAuthResult(
            request_succeeded=False,
            error_code=ErrorCode.AUTH_FAILED,
            error_message="로그인이 필요합니다. .login()을 먼저 호출해주세요."
        )

    def _create_fresh_session(self, service: str) -> MjuUnivAuthResult[requests.Session]:
        """요청마다 독립 세션을 생성해 로그인한다."""
        authenticator = StandardAuthenticator(
            user_id=self._user_id,
            user_pw=self._user_pw,
            verbose=self._verbose,
        )
        return authenticator.login(service)

    # =================================================================
    # 데이터 조회 메서드 (고수준 API)
    # =================================================================

    def get_student_card(self) -> MjuUnivAuthResult[StudentCard]:
        """
        학생카드 정보를 조회합니다.
        MSI 서비스 로그인이 필요하며, 내부적으로 2차 인증을 수행합니다.
        이 메서드는 호출마다 새 세션으로 로그인해 병렬 호출 시 세션 공유를 피합니다.

        Returns:
            MjuUnivAuthResult[StudentCard]: 학생카드 정보 조회 결과
        """
        if self._verbose:
            logger.info("===== mju-univ-auth: 학생카드 조회 =====")
        
            # 1. 이미 로그인된 세션이 있으면 재사용 (체이닝 시 이 경로)
        if self._session is not None:
            session_to_use = self._session
        else:
            # 2. 그렇지 않으면 새 세션으로 로그인 (직접 호출 시 이 경로)
            login_result = self._create_fresh_session(service='msi')
            if not login_result.success:
                return login_result
            session_to_use = login_result.data

        fetcher = StudentCardFetcher(
            session=session_to_use,
            user_pw=self._user_pw,
            verbose=self._verbose,
        )
        return fetcher.fetch()

    def get_student_changelog(self) -> MjuUnivAuthResult[StudentChangeLog]:
        """
        학적변동내역을 조회합니다.
        MSI 서비스 로그인이 필요합니다.
        기존 로그인 세션이 있으면 재사용하고, 없으면 새 세션으로 로그인합니다.
    
        Returns:
            MjuUnivAuthResult[StudentChangeLog]: 학적변동내역 정보 조회 결과
        """
        if self._verbose:
            logger.info("===== mju-univ-auth: 학적변동내역 조회 =====")
    
        # 1. 이미 로그인된 세션이 있으면 재사용 (체이닝 시 이 경로)
        if self._session is not None:
            session_to_use = self._session
        else:
            # 2. 그렇지 않으면 새 세션으로 로그인 (직접 호출 시 이 경로)
            login_result = self._create_fresh_session(service='msi')
            if not login_result.success:
                return login_result
            session_to_use = login_result.data
    
        fetcher = StudentChangeLogFetcher(
            session=session_to_use,
            verbose=self._verbose,
        )
        return fetcher.fetch()
