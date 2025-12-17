"""
학생카드 데이터 모델
==================
순수 데이터 클래스로, 네트워크 로직을 포함하지 않습니다.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Address:
    """주소 정보"""
    postal_code: str = ""
    address: str = ""


@dataclass
class PersonalContact:
    """개인 연락처 정보"""
    english_surname: str = ""
    english_givenname: str = ""
    phone_number: str = ""
    mobile_number: str = ""
    email: str = ""
    current_residence_address: Address = field(default_factory=Address)
    resident_registration_address: Address = field(default_factory=Address)


@dataclass
class StudentProfile:
    """학생 프로필 정보"""
    student_id: str = ""
    name_korean: str = ""
    grade: str = ""
    enrollment_status: str = ""
    college_department: str = ""
    academic_advisor: str = ""
    student_designed_major_advisor: str = ""
    photo_base64: str = ""


@dataclass
class StudentCard:
    """학생카드 정보 데이터 클래스"""
    student_profile: StudentProfile = field(default_factory=StudentProfile)
    personal_contact: PersonalContact = field(default_factory=PersonalContact)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return {
            'student_profile': {
                'student_id': self.student_profile.student_id,
                'name_korean': self.student_profile.name_korean,
                'grade': self.student_profile.grade,
                'enrollment_status': self.student_profile.enrollment_status,
                'college_department': self.student_profile.college_department,
                'academic_advisor': self.student_profile.academic_advisor,
                'student_designed_major_advisor': self.student_profile.student_designed_major_advisor,
                'photo_base64': self.student_profile.photo_base64,
            },
            'personal_contact': {
                'english_surname': self.personal_contact.english_surname,
                'english_givenname': self.personal_contact.english_givenname,
                'phone_number': self.personal_contact.phone_number,
                'mobile_number': self.personal_contact.mobile_number,
                'email': self.personal_contact.email,
                'current_residence_address': {
                    'postal_code': self.personal_contact.current_residence_address.postal_code,
                    'address': self.personal_contact.current_residence_address.address,
                },
                'resident_registration_address': {
                    'postal_code': self.personal_contact.resident_registration_address.postal_code,
                    'address': self.personal_contact.resident_registration_address.address,
                },
            },
        }

    def print_summary(self) -> None:
        """학생 정보 요약 출력"""
        HEADER = '\033[95m'
        CYAN = '\033[96m'
        END = '\033[0m'
        BOLD = '\033[1m'
        
        profile = self.student_profile
        contact = self.personal_contact

        print(f"\n{HEADER}{'='*60}")
        print(f" 학생카드 정보 조회 결과")
        print(f"{'='*60}{END}")
        
        print(f"\n{BOLD}[학생 상세 정보]{END}")
        print(f"  {CYAN}학번:{END} {profile.student_id}")
        print(f"  {CYAN}한글성명:{END} {profile.name_korean}")
        print(f"  {CYAN}학년:{END} {profile.grade}")
        print(f"  {CYAN}학적상태:{END} {profile.enrollment_status}")
        print(f"  {CYAN}학부(과):{END} {profile.college_department}")
        print(f"  {CYAN}상담교수:{END} {profile.academic_advisor}")
        if profile.student_designed_major_advisor:
            print(f"  {CYAN}학생설계전공지도교수:{END} {profile.student_designed_major_advisor}")
        if profile.photo_base64:
            print(f"  {CYAN}증명사진:{END} Base64 ({len(profile.photo_base64)} chars)")
        
        print(f"\n{BOLD}[개인 연락처 정보]{END}")
        print(f"  {CYAN}영문성명(성):{END} {contact.english_surname}")
        print(f"  {CYAN}영문성명(이름):{END} {contact.english_givenname}")
        print(f"  {CYAN}전화번호:{END} {contact.phone_number}")
        print(f"  {CYAN}휴대폰:{END} {contact.mobile_number}")
        print(f"  {CYAN}E-Mail:{END} {contact.email}")
        print(f"  {CYAN}현거주지 주소:{END} ({contact.current_residence_address.postal_code}) {contact.current_residence_address.address}")
        print(f"  {CYAN}주민등록 주소:{END} ({contact.resident_registration_address.postal_code}) {contact.resident_registration_address.address}")