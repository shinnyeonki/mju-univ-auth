"""
수강신청 강의 정보 도메인 모델
==============================
강의 검색 API 응답 데이터를 담는 클래스입니다.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Lecture:
    """
    강의 정보 데이터 클래스
    
    수강신청 시스템의 강의 검색 결과를 담습니다.
    """
    # 기본 정보
    course_cls: str              # 강좌번호 (coursecls)
    curi_nm: str                 # 강의명 (curinm)
    prof_nm: str                 # 교수명 (profnm)
    credit: str                  # 학점 (cdtnum)
    
    # 시간 및 장소
    lec_time_room: Optional[str] # 시간/강의실 (lecttime)
    
    # 수강 인원
    limit_cnt: str               # 정원 (takelim)
    sugang_cnt: str              # 수강신청 인원 (listennow)
    
    # 분류 정보
    dept_nm: str                 # 학과명 (deptnm)
    dept_cd: str                 # 학과코드 (deptcd)
    campus_div: str              # 캠퍼스 구분 (campusdiv)
    
    # 학기 정보
    curi_year: str               # 개설 연도 (curiyear)
    curi_smt: str                # 학기 코드 (curismt)
    
    # 과목 정보
    curi_num: str                # 과목 번호 (curinum)
    curi_num2: Optional[str]     # 과목 약어 (curinum2)
    group_cd: Optional[str]      # 그룹 코드 (groupcd)
    class_div: str               # 분반 (classdiv)
    gbn: str                     # 수강 구분 (gbn)
    
    # 기타 정보
    sugang_yn: str               # 수강신청 가능 여부 (sugyn)
    class_type: str              # 수업 유형 (classtype)
    flex_yn: str                 # 플렉스 여부 (flexyn)
    internet_yn: Optional[str]   # 온라인 강의 여부 (internetyn)
    
    # 원본 데이터 (필요시 추가 필드 접근용)
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Lecture':
        """API 응답 딕셔너리에서 Lecture 객체 생성"""
        return cls(
            course_cls=str(data.get("coursecls", "")),
            curi_nm=str(data.get("curinm", "")),
            prof_nm=str(data.get("profnm", "미배정")),
            credit=str(data.get("cdtnum", "")),
            lec_time_room=data.get("lecttime"),
            limit_cnt=str(data.get("takelim", "")),
            sugang_cnt=str(data.get("listennow", "")),
            dept_nm=str(data.get("deptnm", "")),
            dept_cd=str(data.get("deptcd", "")),
            campus_div=str(data.get("campusdiv", "")),
            curi_year=str(data.get("curiyear", "")),
            curi_smt=str(data.get("curismt", "")),
            curi_num=str(data.get("curinum", "")),
            curi_num2=data.get("curinum2"),
            group_cd=data.get("groupcd"),
            class_div=str(data.get("classdiv", "")),
            gbn=str(data.get("gbn", "")),
            sugang_yn=str(data.get("sugyn", "N")),
            class_type=str(data.get("classtype", "")),
            flex_yn=str(data.get("flexyn", "N")),
            internet_yn=data.get("internetyn"),
            raw_data=data,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """객체를 딕셔너리로 변환"""
        return {
            "course_cls": self.course_cls,
            "curi_nm": self.curi_nm,
            "prof_nm": self.prof_nm,
            "credit": self.credit,
            "lec_time_room": self.lec_time_room,
            "limit_cnt": self.limit_cnt,
            "sugang_cnt": self.sugang_cnt,
            "dept_nm": self.dept_nm,
            "dept_cd": self.dept_cd,
            "campus_div": self.campus_div,
            "curi_year": self.curi_year,
            "curi_smt": self.curi_smt,
            "curi_num": self.curi_num,
            "curi_num2": self.curi_num2,
            "group_cd": self.group_cd,
            "class_div": self.class_div,
            "gbn": self.gbn,
            "sugang_yn": self.sugang_yn,
            "class_type": self.class_type,
            "flex_yn": self.flex_yn,
            "internet_yn": self.internet_yn,
        }
    
    @property
    def is_available(self) -> bool:
        """수강신청 가능 여부"""
        return self.sugang_yn == "Y"
    
    @property
    def remaining_seats(self) -> int:
        """잔여석"""
        try:
            return int(self.limit_cnt) - int(self.sugang_cnt)
        except (ValueError, TypeError):
            return 0
    
    @property
    def campus_name(self) -> str:
        """캠퍼스 이름"""
        return "자연캠퍼스" if self.campus_div == "10" else "인문캠퍼스"
    
    @property
    def semester_name(self) -> str:
        """학기 이름"""
        return "1학기" if self.curi_smt == "10" else "2학기"


@dataclass
class LectureSearchResult:
    """
    강의 검색 결과 컨테이너
    
    Attributes:
        lectures: 검색된 강의 목록
        total_count: 총 강의 수
    """
    lectures: List[Lecture] = field(default_factory=list)
    
    @property
    def total_count(self) -> int:
        return len(self.lectures)
    
    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]]) -> 'LectureSearchResult':
        """API 응답 리스트에서 LectureSearchResult 생성"""
        lectures = [Lecture.from_dict(item) for item in data_list]
        return cls(lectures=lectures)
    
    def __iter__(self):
        return iter(self.lectures)
    
    def __len__(self):
        return len(self.lectures)
    
    def __getitem__(self, index):
        return self.lectures[index]
