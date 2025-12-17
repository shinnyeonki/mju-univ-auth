"""도메인 모델 - 순수 데이터 클래스"""

from .student_basicinfo import StudentBasicInfo
from .student_card import StudentCard, StudentProfile, PersonalContact, Address
from .student_changelog import StudentChangeLog, AcademicStatus, ChangeLogEntry

__all__ = [
    'StudentBasicInfo',
    'StudentCard',
    'StudentProfile',
    'PersonalContact',
    'Address',
    'StudentChangeLog',
    'AcademicStatus',
    'ChangeLogEntry',
]