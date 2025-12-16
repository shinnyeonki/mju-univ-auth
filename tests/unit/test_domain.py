import pytest
from mju_univ_auth.domain import StudentCard, StudentChangeLog

@pytest.fixture
def student_card_parsed_fields():
    """Provides a sample dictionary of parsed fields for a StudentCard."""
    return {
        '학번': '60200001',
        '한글성명': '홍길동',
        '영문성명(성)': 'HONG',
        '영문성명(이름)': 'GILDONG',
        '학년': '3학년',
        '학적상태': '재학',
        '학부(과)': '컴퓨터공학과',
        '상담교수': '김교수',
        '학생설계전공지도교수': '박교수',
        'phone': '02-123-4567',
        'mobile': '010-1234-5678',
        'email': 'test@mju.ac.kr',
        'current_zip': '12345',
        'current_address1': '서울시 서대문구',
        'current_address2': '거북골로 34',
        'registered_zip': '54321',
        'registered_address1': '경기도 용인시',
        'registered_address2': '처인구 남동',
        'photo_base64': 'base64encodedstring',
        'focus_newsletter': True,
    }

@pytest.fixture
def student_changelog_parsed_fields():
    """Provides a sample dictionary of parsed fields for a StudentChangeLog."""
    return {
        '학번': '60200001',
        '성명': '홍길동',
        '학적상태': '재학',
        '학년': '3',
        '이수학기': '6',
        '학부(과)': '컴퓨터공학과',
    }

class TestStudentCard:
    def test_from_parsed_fields(self, student_card_parsed_fields):
        """Tests creating a StudentCard from a dictionary."""
        card = StudentCard.from_parsed_fields(student_card_parsed_fields)

        assert card.student_id == '60200001'
        assert card.name_korean == '홍길동'
        assert card.name_english_first == 'HONG'
        assert card.name_english_last == 'GILDONG'
        assert card.grade == '3'
        assert card.status == '재학'
        assert card.department == '컴퓨터공학과'
        assert card.advisor == '김교수'
        assert card.design_advisor == '박교수'
        assert card.phone == '02-123-4567'
        assert card.mobile == '010-1234-5678'
        assert card.email == 'test@mju.ac.kr'
        assert card.current_zip == '12345'
        assert card.current_address1 == '서울시 서대문구'
        assert card.current_address2 == '거북골로 34'
        assert card.registered_zip == '54321'
        assert card.registered_address1 == '경기도 용인시'
        assert card.registered_address2 == '처인구 남동'
        assert card.photo_base64 == 'base64encodedstring'
        assert card.focus_newsletter is True
        assert card.raw_data == student_card_parsed_fields

    def test_computed_properties(self):
        """Tests computed properties like name_english and addresses."""
        card = StudentCard(
            name_english_first="HONG",
            name_english_last="GILDONG",
            current_zip="12345",
            current_address1="서울시 서대문구",
            current_address2="거북골로 34",
            registered_zip="54321",
            registered_address1="경기도 용인시",
            registered_address2="처인구 남동",
        )
        assert card.name_english == "HONG GILDONG"
        assert card.current_address == "(12345) 서울시 서대문구 거북골로 34"
        assert card.registered_address == "(54321) 경기도 용인시 처인구 남동"

    def test_to_dict(self, student_card_parsed_fields):
        """Tests converting a StudentCard instance to a dictionary."""
        card = StudentCard.from_parsed_fields(student_card_parsed_fields)
        card_dict = card.to_dict()

        assert card_dict['student_id'] == '60200001'
        assert card_dict['name_korean'] == '홍길동'
        assert card_dict['name_english'] == 'HONG GILDONG'
        assert card_dict['grade'] == '3'
        assert card_dict['status'] == '재학'
        assert card_dict['department'] == '컴퓨터공학과'
        assert card_dict['current_address'] == '(12345) 서울시 서대문구 거북골로 34'
        assert card_dict['photo_base64'] == 'base64encodedstring'


class TestStudentChangeLog:
    def test_from_parsed_fields(self, student_changelog_parsed_fields):
        """Tests creating a StudentChangeLog from a dictionary."""
        log = StudentChangeLog.from_parsed_fields(student_changelog_parsed_fields)

        assert log.student_id == '60200001'
        assert log.name == '홍길동'
        assert log.status == '재학'
        assert log.grade == '3'
        assert log.completed_semesters == '6'
        assert log.department == '컴퓨터공학과'

    def test_to_dict(self, student_changelog_parsed_fields):
        """Tests converting a StudentChangeLog instance to a dictionary."""
        log = StudentChangeLog.from_parsed_fields(student_changelog_parsed_fields)
        log_dict = log.to_dict()

        assert log_dict['student_id'] == '60200001'
        assert log_dict['name'] == '홍길동'
        assert log_dict['status'] == '재학'
