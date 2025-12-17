"""
학생카드 데이터 모델
==================
순수 데이터 클래스로, 네트워크 로직을 포함하지 않습니다.
"""

from typing import Dict, Any
from pydantic import BaseModel, Field


class Address(BaseModel):
    """주소 정보"""
    postal_code: str = ""
    address: str = ""


class PersonalContact(BaseModel):
    """개인 연락처 정보"""
    english_surname: str = ""
    english_givenname: str = ""
    phone_number: str = ""
    mobile_number: str = ""
    email: str = ""
    current_residence_address: Address = Field(default_factory=Address)
    resident_registration_address: Address = Field(default_factory=Address)


class StudentProfile(BaseModel):
    """학생 프로필 정보"""
    student_id: str = ""
    name_korean: str = ""
    grade: str = ""
    enrollment_status: str = ""
    college_department: str = ""
    academic_advisor: str = ""
    student_designed_major_advisor: str = ""
    photo_base64: str = ""


class StudentCard(BaseModel):
    """학생카드 정보 데이터 클래스"""
    student_profile: StudentProfile = Field(default_factory=StudentProfile)
    personal_contact: PersonalContact = Field(default_factory=PersonalContact)
    raw_html_data: str = ""

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