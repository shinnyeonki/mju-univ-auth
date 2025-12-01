"""
학적변동내역 데이터 모델
=======================
순수 데이터 클래스로, 네트워크 로직을 포함하지 않습니다.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class StudentChangeLog:
    """학적변동내역 정보 데이터 클래스"""
    
    student_id: str = ""           # 학번
    name: str = ""                 # 성명
    status: str = ""               # 학적상태
    grade: str = ""                # 학년
    completed_semesters: str = ""  # 이수학기
    department: str = ""           # 학부(과)
    
    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return {
            'student_id': self.student_id,
            'name': self.name,
            'status': self.status,
            'grade': self.grade,
            'completed_semesters': self.completed_semesters,
            'department': self.department,
        }
    
    def print_summary(self) -> None:
        """학적변동내역 정보 요약 출력"""
        # ANSI 컬러 코드
        HEADER = '\033[95m'
        CYAN = '\033[96m'
        END = '\033[0m'
        
        print(f"\n{HEADER}{'='*60}")
        print(f" 학적변동내역 조회 결과")
        print(f"{'='*60}{END}")
        
        print(f"  {CYAN}학번:{END} {self.student_id}")
        print(f"  {CYAN}성명:{END} {self.name}")
        print(f"  {CYAN}학적상태:{END} {self.status}")
        print(f"  {CYAN}학년:{END} {self.grade}")
        print(f"  {CYAN}이수학기:{END} {self.completed_semesters}")
        print(f"  {CYAN}학부(과):{END} {self.department}")
    
    @classmethod
    def from_parsed_fields(cls, fields: Dict[str, str]) -> 'StudentChangeLog':
        """파싱된 필드 딕셔너리에서 StudentChangeLog 객체 생성"""
        return cls(
            student_id=fields.get('학번', ''),
            name=fields.get('성명', ''),
            status=fields.get('학적상태', ''),
            grade=fields.get('학년', ''),
            completed_semesters=fields.get('이수학기', ''),
            department=fields.get('학부(과)', ''),
        )
