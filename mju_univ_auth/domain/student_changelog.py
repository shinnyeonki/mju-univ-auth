"""
학적변동내역 데이터 모델
=======================
순수 데이터 클래스로, 네트워크 로직을 포함하지 않습니다.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class AcademicStatus:
    """학적 기본 정보"""
    student_id: str = ""
    name: str = ""
    status: str = ""
    grade: str = ""
    completed_semesters: str = ""
    department: str = ""


@dataclass
class ChangeLogEntry:
    """변동 내역 리스트 항목"""
    year: str = ""
    semester: str = ""
    change_type: str = ""
    change_date: str = ""
    expiry_date: str = ""
    reason: str = ""


@dataclass
class StudentChangeLog:
    """학적변동내역 정보 데이터 클래스"""
    academic_status: AcademicStatus = field(default_factory=AcademicStatus)
    cumulative_leave_semesters: str = ""
    change_log_list: List[ChangeLogEntry] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return {
            'academic_status': {
                'student_id': self.academic_status.student_id,
                'name': self.academic_status.name,
                'status': self.academic_status.status,
                'grade': self.academic_status.grade,
                'completed_semesters': self.academic_status.completed_semesters,
                'department': self.academic_status.department,
            },
            'leave_history': {
                'cumulative_leave_semesters': self.cumulative_leave_semesters,
            },
            'change_log_list': [
                {
                    'year': entry.year,
                    'semester': entry.semester,
                    'change_type': entry.change_type,
                    'change_date': entry.change_date,
                    'expiry_date': entry.expiry_date,
                    'reason': entry.reason,
                } for entry in self.change_log_list
            ]
        }

    def print_summary(self) -> None:
        """학적변동내역 정보 요약 출력"""
        HEADER = '\033[95m'
        CYAN = '\033[96m'
        END = '\033[0m'
        BOLD = '\033[1m'

        print(f"\n{HEADER}{'='*60}")
        print(f" 학적변동내역 조회 결과")
        print(f"{'='*60}{END}")
        
        print(f"\n{BOLD}[학적 기본 정보]{END}")
        print(f"  {CYAN}학번:{END} {self.academic_status.student_id}")
        print(f"  {CYAN}성명:{END} {self.academic_status.name}")
        print(f"  {CYAN}학적상태:{END} {self.academic_status.status}")
        print(f"  {CYAN}학년:{END} {self.academic_status.grade}")
        print(f"  {CYAN}이수학기:{END} {self.academic_status.completed_semesters}")
        print(f"  {CYAN}학부(과):{END} {self.academic_status.department}")

        print(f"\n{BOLD}[휴학 누적 현황]{END}")
        print(f"  {CYAN}누적 휴학 학기:{END} {self.cumulative_leave_semesters}")

        print(f"\n{BOLD}[변동 내역]{END}")
        if not self.change_log_list:
            print("  변동 내역이 없습니다.")
        else:
            for entry in self.change_log_list:
                print(f"  - {entry.year}년 {entry.semester}: {entry.change_type} ({entry.change_date} ~ {entry.expiry_date or 'N/A'})")