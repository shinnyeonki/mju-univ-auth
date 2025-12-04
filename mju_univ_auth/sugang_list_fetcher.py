"""
수강신청 강의 목록 Fetcher
===========================
수강신청 시스템에서 강의 목록을 조회하는 클래스입니다.
"""

import json
from typing import Optional, Tuple
import requests
import logging

from .base_fetcher import BaseFetcher
from .config import SERVICES, TIMEOUT_CONFIG
from .domain.lecture import Lecture, LectureSearchResult
from .domain.lecture_search_request import LectureSearchRequest
from .results import MjuUnivAuthResult, ErrorCode
from .exceptions import (
    NetworkError,
    PageParsingError,
    SessionExpiredError,
)

logger = logging.getLogger(__name__)


class SugangListFetcher(BaseFetcher[LectureSearchResult]):
    """
    수강신청 시스템에서 강의 목록을 조회하는 Fetcher
    
    SugangAuthenticator로 로그인한 세션을 사용하여 강의를 검색합니다.
    """
    
    def __init__(
        self,
        session: requests.Session,
        csrf_token: str,
        csrf_header: str,
        verbose: bool = False,
    ):
        """
        Args:
            session: 로그인된 requests.Session 객체
            csrf_token: AJAX 요청용 CSRF 토큰
            csrf_header: CSRF 헤더 이름 (예: "X-CSRF-TOKEN")
            verbose: 상세 로그 출력 여부
        """
        super().__init__(session)
        self._csrf_token = csrf_token
        self._csrf_header = csrf_header
        self._verbose = verbose
        self._search_request: Optional[LectureSearchRequest] = None
        
        # config에서 endpoints 가져오기
        self._endpoints = SERVICES['sugang'].endpoints
    
    def search(self, request: LectureSearchRequest) -> MjuUnivAuthResult[LectureSearchResult]:
        """
        강의 검색 수행
        
        Args:
            request: 강의 검색 요청 객체
            
        Returns:
            MjuUnivAuthResult[LectureSearchResult]: 검색 결과
        """
        self._search_request = request
        return self.fetch()
    
    def _execute(self) -> LectureSearchResult:
        """강의 검색 실행"""
        if self._search_request is None:
            raise ValueError("검색 요청이 설정되지 않았습니다. search() 메서드를 사용하세요.")
        
        if self._verbose:
            logger.info(f"[강의 검색] {self._search_request.to_request_dict()}")
        
        # 요청 데이터 구성
        request_data = self._search_request.to_request_dict()
        
        # 헤더 구성
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self._endpoints.MAIN}?lang=ko",
            self._csrf_header: self._csrf_token,
        }
        
        # AJAX 요청
        try:
            response = self.session.post(
                self._endpoints.LECTURE_SEARCH,
                data=request_data,
                headers=headers,
                timeout=TIMEOUT_CONFIG.default,
            )
        except requests.RequestException as e:
            raise NetworkError(
                "강의 검색 요청 실패",
                url=self._endpoints.LECTURE_SEARCH,
                original_error=e
            )
        
        # 403 처리 (CSRF 토큰 만료)
        if response.status_code == 403:
            if self._verbose:
                logger.warning("403 Forbidden - CSRF 토큰이 만료되었을 수 있습니다.")
            raise SessionExpiredError("CSRF 토큰이 만료되었습니다. 재로그인이 필요합니다.")
        
        # 기타 HTTP 에러
        if response.status_code != 200:
            raise NetworkError(
                f"강의 검색 실패 (HTTP {response.status_code})",
                url=self._endpoints.LECTURE_SEARCH
            )
        
        # JSON 파싱
        try:
            lectures_data = response.json()
        except json.JSONDecodeError as e:
            if self._verbose:
                logger.error(f"JSON 파싱 오류: {response.text[:500]}")
            raise PageParsingError("강의 검색 응답 파싱 실패", field="json")
        
        # 응답 형식 검증
        if not isinstance(lectures_data, list):
            raise PageParsingError(
                f"예상치 못한 응답 형식: {type(lectures_data).__name__}",
                field="response_type"
            )
        
        if self._verbose:
            logger.info(f"✓ {len(lectures_data)}개 강의 검색 완료")
        
        return LectureSearchResult.from_list(lectures_data)
    
    def update_csrf(self, csrf_token: str, csrf_header: str) -> None:
        """
        CSRF 토큰 업데이트
        
        Args:
            csrf_token: 새 CSRF 토큰
            csrf_header: 새 CSRF 헤더명
        """
        self._csrf_token = csrf_token
        self._csrf_header = csrf_header
