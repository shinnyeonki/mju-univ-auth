"""
인증 관리자 모듈
================
다양한 인증 방식을 통합 관리하는 Authenticator 클래스를 정의합니다.
서비스 이름에 따라 적절한 인증 구현체(StandardAuthenticator 등)를 선택하여 실행합니다.
"""

import requests

from .results import MjuUnivAuthResult
from .standard_authenticator import StandardAuthenticator
from .sugang_authenticator import SugangAuthenticator


class Authenticator:
    """
    다양한 인증 방식(Standard, Library 등)을 통합 관리하는 클래스
    
    서비스 이름에 따라 적절한 인증 구현체를 선택하여 실행합니다.
    현재는 StandardAuthenticator만 지원하며, 추후 도서관 등 특수 인증 방식 추가 시
    이 클래스에서 라우팅 로직만 추가하면 됩니다.
    
    사용 예시:
    ```python
    from mju_univ_auth import Authenticator
    
    auth = Authenticator(user_id="학번", user_pw="비밀번호")
    result = auth.login("msi")
    
    if result.success:
        session = result.data  # requests.Session 객체
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

    def login(self, service: str = 'msi') -> MjuUnivAuthResult[requests.Session]:
        """
        서비스 이름에 맞는 인증기를 찾아 로그인을 수행합니다.
        
        Args:
            service: 로그인할 서비스
                - SSO 기반: 'main', 'msi', 'lms', 'portal', 'myicap', 'intern', 'ipp', 'ucheck'
                - 수강신청: 'sugang', 'class'
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 로그인 결과
        """
        # 1. 수강신청 시스템 (별도 인증 체계)
        if service in ('sugang', 'class'):
            auth = SugangAuthenticator(
                user_id=self._user_id,
                user_pw=self._user_pw,
                service='sugang',
                verbose=self._verbose
            )
            return auth.authenticate()
        
        # 2. 기본 SSO 서비스 처리 (MSI, LMS, MyiCAP 등 대부분)
        auth = StandardAuthenticator(
            user_id=self._user_id,
            user_pw=self._user_pw,
            service=service,
            verbose=self._verbose
        )
        
        return auth.authenticate()
