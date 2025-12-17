import pytest
from unittest.mock import MagicMock
from mju_univ_auth.fetcher.student_card_fetcher import StudentCardFetcher
from mju_univ_auth.domain.student_card import StudentCard
from mju_univ_auth.results import MjuUnivAuthResult

# A minimal but realistic HTML snippet for the student card page
STUDENT_CARD_HTML = """
<html>
<body>
    <div id="pictureInclude">
        <img src="data:image/jpg;base64,FAKEDATA" />
        <div class="flex-table">
            <div class="flex-table-item">
                <div class="item-title">학번</div>
                <div class="item-data">60200001</div>
            </div>
            <div class="flex-table-item">
                <div class="item-title">한글성명</div>
                <div class="item-data">김명지</div>
            </div>
        </div>
    </div>
    <hr />
    <div class="flex-table">
        <input name="nm_eng" value="KIM" />
        <input name="nm_eng2" value="MYONGJI" />
        <input name="std_tel" value="02-123-4567" />
        <input name="htel" value="010-1234-5678" />
        <input name="email" value="test@mju.ac.kr" />
        <input name="zip1" value="123" />
        <input name="zip2" value="456" />
        <input name="addr1" value="서울특별시" />
        <input name="addr2" value="서대문구" />
        <input name="zip1_2" value="111" />
        <input name="zip2_2" value="222" />
        <input name="addr1_2" value="경기도" />
        <input name="addr2_2" value="용인시" />
    </div>
</body>
</html>
"""

@pytest.fixture
def mock_fetcher(monkeypatch):
    """Provides a StudentCardFetcher with mocked network calls."""
    mock_session = MagicMock()
    fetcher = StudentCardFetcher(session=mock_session, user_pw='pw')
    
    # Mock methods that perform network calls or depend on previous steps
    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: None)
    monkeypatch.setattr(fetcher, '_is_password_required', lambda html: False)
    return fetcher

def test_student_card_fetcher_success(mock_fetcher, monkeypatch):
    """Tests that the fetcher correctly parses a valid HTML."""
    # Arrange: Make _access_student_card_page return our sample HTML
    monkeypatch.setattr(mock_fetcher, '_access_student_card_page', lambda: STUDENT_CARD_HTML)

    # Act
    result = mock_fetcher.fetch()

    # Assert
    assert result.success
    card = result.data
    assert isinstance(card, StudentCard)
    assert card.student_profile.student_id == '60200001'
    assert card.student_profile.name_korean == '김명지'
    assert card.personal_contact.email == 'test@mju.ac.kr'
    assert card.personal_contact.current_residence_address.postal_code == '123-456'

def test_student_card_fetcher_parse_error(mock_fetcher, monkeypatch):
    """Tests that the fetcher returns a ParsingError for invalid HTML."""
    # Arrange: Return empty HTML
    monkeypatch.setattr(mock_fetcher, '_access_student_card_page', lambda: "<html></html>")

    # Act
    result = mock_fetcher.fetch()

    # Assert
    assert not result.success
    assert result.error_code == 'PARSING_ERROR'
    assert '학생 프로필 테이블을 찾을 수 없습니다' in result.error_message