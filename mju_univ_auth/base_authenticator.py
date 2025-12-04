"""
인증기 기본 클래스
==================
모든 Authenticator 구현체가 상속받는 추상 기본 클래스입니다.
"""

from abc import ABC, abstractmethod
from typing import Optional
import requests

from .results import MjuUnivAuthResult


class BaseAuthenticator(ABC):
    """
    인증기의 추상 기본 클래스
    
    모든 인증 방식(Standard SSO, Library 등)이 이 클래스를 상속받아
    authenticate() 메서드를 구현합니다.
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

    @abstractmethod
    def authenticate(self) -> MjuUnivAuthResult[requests.Session]:
        """
        인증을 수행하고 결과를 반환합니다.
        
        Returns:
            MjuUnivAuthResult[requests.Session]: 인증 결과
                - 성공 시: data에 로그인된 Session 객체
                - 실패 시: error_code와 error_message 포함
        """
        pass
