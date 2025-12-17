
"""
학생 기본 정보 데이터 모델
========================
MSI 메인 페이지의 대시보드 요약 정보를 담는 순수 데이터 클래스입니다.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class StudentBasicInfo(BaseModel):
    """학생 기본 정보(대시보드 요약) 데이터 클래스"""
    department: str = Field(default="", description="소속")
    category: str = Field(default="", description="구분")
    grade: str = Field(default="", description="학년")
    last_access_time: str = Field(default="", description="최근 접속 시간")
    last_access_ip: str = Field(default="", description="최근 접속 IP")
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    def print_summary(self) -> None:
        """학생 기본 정보 요약 출력"""
        HEADER = '\033[95m'
        CYAN = '\033[96m'
        END = '\033[0m'
        
        print(f"\n{HEADER}{'='*60}")
        print(f" 학생 기본 정보(대시보드) 조회 결과")
        print(f"{'='*60}{END}")
        
        print(f"  {CYAN}소속:{END} {self.department}")
        print(f"  {CYAN}구분:{END} {self.category}")
        print(f"  {CYAN}학년:{END} {self.grade}")
        print(f"  {CYAN}최근 접속 시간:{END} {self.last_access_time}")
        print(f"  {CYAN}최근 접속 IP:{END} {self.last_access_ip}")

