"""
수강신청 강의 검색 요청 DTO
===========================
강의 검색 API 요청에 사용되는 데이터 클래스입니다.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class LectureSearchRequest:
    """
    강의 검색 요청 데이터 클래스
    
    Attributes:
        campus_div: 캠퍼스 구분 ("10": 자연캠퍼스, "20": 인문캠퍼스)
        dept_cd: 학과 코드
        display_div: 소분류 (교양 과목 분류 등)
        search_type: 검색 타입 ("1": 기본값, "2": 키워드 검색)
        course_cls: 강좌번호 (키워드 검색시 사용)
        curi_nm: 과목명 검색
        exclude_day: 제외 요일
    """
    campus_div: str = "10"
    dept_cd: str = "10000"
    display_div: str = "01"
    search_type: str = "1"
    course_cls: str = ""
    curi_nm: str = ""
    exclude_day: str = ""
    
    def to_request_dict(self) -> Dict[str, str]:
        """API 요청용 딕셔너리로 변환 (카멜케이스 키 사용)"""
        return {
            "courseCls": self.course_cls,
            "curiNm": self.curi_nm,
            "campusDiv": self.campus_div,
            "deptCd": self.dept_cd,
            "displayDiv": self.display_div,
            "searchType": self.search_type,
            "excludeDay": self.exclude_day,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LectureSearchRequest':
        """딕셔너리에서 객체 생성 (카멜케이스/스네이크케이스 모두 지원)"""
        return cls(
            campus_div=data.get("campusDiv", data.get("campus_div", "10")),
            dept_cd=data.get("deptCd", data.get("dept_cd", "10000")),
            display_div=data.get("displayDiv", data.get("display_div", "01")),
            search_type=data.get("searchType", data.get("search_type", "1")),
            course_cls=data.get("courseCls", data.get("course_cls", "")),
            curi_nm=data.get("curiNm", data.get("curi_nm", "")),
            exclude_day=data.get("excludeDay", data.get("exclude_day", "")),
        )
