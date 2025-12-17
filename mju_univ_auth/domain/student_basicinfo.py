
"""
학생 기본 정보 데이터 모델
========================
MSI 메인 페이지의 대시보드 요약 정보를 담는 순수 데이터 클래스입니다.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class StudentBasicInfo:
    """학생 기본 정보(대시보드 요약) 데이터 클래스"""
    department: str = ""           # 소속
    category: str = ""             # 구분
    grade: str = ""                # 학년
    last_access_time: str = ""     # 최근 접속 시간
    last_access_ip: str = ""       # 최근 접속 IP
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return {
            'department': self.department,
            'category': self.category,
            'grade': self.grade,
            'last_access_time': self.last_access_time,
            'last_access_ip': self.last_access_ip,
        }

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

