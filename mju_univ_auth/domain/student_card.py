"""
학생카드 데이터 모델
==================
순수 데이터 클래스로, 네트워크 로직을 포함하지 않습니다.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class StudentCard:
    """학생카드 정보 데이터 클래스"""
    
    # 기본 정보
    student_id: str = ""           # 학번
    name_korean: str = ""          # 한글성명
    name_english_first: str = ""   # 영문성명(성)
    name_english_last: str = ""    # 영문성명(이름)
    
    # 학적 정보
    grade: str = ""                # 학년
    status: str = ""               # 학적상태 (재학, 휴학 등)
    department: str = ""           # 학부(과)
    advisor: str = ""              # 상담교수
    design_advisor: str = ""       # 학생설계전공지도교수
    
    # 연락처 정보
    phone: str = ""                # 전화번호
    mobile: str = ""               # 휴대폰
    email: str = ""                # 이메일
    
    # 주소 정보
    current_zip: str = ""          # 현거주지 우편번호
    current_address1: str = ""     # 현거주지 주소1
    current_address2: str = ""     # 현거주지 주소2
    registered_zip: str = ""       # 주민등록 우편번호
    registered_address1: str = ""  # 주민등록 주소1
    registered_address2: str = ""  # 주민등록 주소2
    
    # 사진 (Base64)
    photo_base64: str = ""
    
    # 기타
    focus_newsletter: bool = False  # 명지포커스 수신여부
    
    # 원본 데이터 (딕셔너리)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def name_english(self) -> str:
        """영문 성명 전체"""
        return f"{self.name_english_first} {self.name_english_last}".strip()
    
    @property
    def current_address(self) -> str:
        """현거주지 전체 주소"""
        return f"({self.current_zip}) {self.current_address1} {self.current_address2}".strip()
    
    @property
    def registered_address(self) -> str:
        """주민등록 전체 주소"""
        return f"({self.registered_zip}) {self.registered_address1} {self.registered_address2}".strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return {
            'student_id': self.student_id,
            'name_korean': self.name_korean,
            'name_english': self.name_english,
            'grade': self.grade,
            'status': self.status,
            'department': self.department,
            'advisor': self.advisor,
            'design_advisor': self.design_advisor,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': self.email,
            'current_address': self.current_address,
            'registered_address': self.registered_address,
            'photo_base64': self.photo_base64,
            'focus_newsletter': self.focus_newsletter,
        }
    
    def print_summary(self) -> None:
        """학생 정보 요약 출력"""
        from ..utils import Colors
        
        print(f"\n{Colors.HEADER}{'='*60}")
        print(f" 학생카드 정보 조회 결과")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}")
        
        print(f"\n{Colors.BOLD}[기본 정보]{Colors.END}")
        print(f"  {Colors.CYAN}학번:{Colors.END} {self.student_id}")
        print(f"  {Colors.CYAN}한글성명:{Colors.END} {self.name_korean}")
        print(f"  {Colors.CYAN}영문성명:{Colors.END} {self.name_english}")
        
        print(f"\n{Colors.BOLD}[학적 정보]{Colors.END}")
        print(f"  {Colors.CYAN}학년:{Colors.END} {self.grade}")
        print(f"  {Colors.CYAN}학적상태:{Colors.END} {self.status}")
        print(f"  {Colors.CYAN}학부(과):{Colors.END} {self.department}")
        print(f"  {Colors.CYAN}상담교수:{Colors.END} {self.advisor}")
        if self.design_advisor:
            print(f"  {Colors.CYAN}학생설계전공지도교수:{Colors.END} {self.design_advisor}")
        
        print(f"\n{Colors.BOLD}[연락처]{Colors.END}")
        print(f"  {Colors.CYAN}전화번호:{Colors.END} {self.phone}")
        print(f"  {Colors.CYAN}휴대폰:{Colors.END} {self.mobile}")
        print(f"  {Colors.CYAN}E-Mail:{Colors.END} {self.email}")
        
        print(f"\n{Colors.BOLD}[주소]{Colors.END}")
        print(f"  {Colors.CYAN}현거주지:{Colors.END} {self.current_address}")
        print(f"  {Colors.CYAN}주민등록:{Colors.END} {self.registered_address}")
        
        if self.photo_base64:
            print(f"\n{Colors.BOLD}[사진]{Colors.END}")
            print(f"  {Colors.CYAN}사진 데이터:{Colors.END} Base64 ({len(self.photo_base64)} chars)")
    
    @classmethod
    def from_parsed_fields(cls, fields: Dict[str, Any]) -> 'StudentCard':
        """파싱된 필드 딕셔너리에서 StudentCard 객체 생성"""
        card = cls()
        card.raw_data = fields.copy()
        
        # 기본 매핑
        field_mapping = {
            '학번': 'student_id',
            '한글성명': 'name_korean',
            '영문성명(성)': 'name_english_first',
            '영문성명(이름)': 'name_english_last',
            '학적상태': 'status',
            '학부(과)': 'department',
            '상담교수': 'advisor',
            '학생설계전공지도교수': 'design_advisor',
        }
        
        for korean, english in field_mapping.items():
            if korean in fields:
                setattr(card, english, fields[korean])
        
        # 학년 (숫자만 추출)
        if '학년' in fields:
            card.grade = fields['학년'].replace('학년', '').strip()
        
        # 특수 필드
        if 'phone' in fields:
            card.phone = fields['phone']
        if 'mobile' in fields:
            card.mobile = fields['mobile']
        if 'email' in fields:
            card.email = fields['email']
        if 'photo_base64' in fields:
            card.photo_base64 = fields['photo_base64']
        
        # 주소
        if 'current_zip' in fields:
            card.current_zip = fields['current_zip']
        if 'current_address1' in fields:
            card.current_address1 = fields['current_address1']
        if 'current_address2' in fields:
            card.current_address2 = fields['current_address2']
        if 'registered_zip' in fields:
            card.registered_zip = fields['registered_zip']
        if 'registered_address1' in fields:
            card.registered_address1 = fields['registered_address1']
        if 'registered_address2' in fields:
            card.registered_address2 = fields['registered_address2']
        
        # 기타
        if 'focus_newsletter' in fields:
            card.focus_newsletter = fields['focus_newsletter']
        
        return card
