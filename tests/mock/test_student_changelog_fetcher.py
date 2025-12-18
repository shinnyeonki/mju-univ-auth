import pytest
from unittest.mock import MagicMock
from mju_univ_auth.fetcher.student_changelog_fetcher import StudentChangeLogFetcher
from mju_univ_auth.domain.student_changelog import StudentChangeLog
from mju_univ_auth.exceptions import ParsingError

# A minimal but realistic HTML snippet for the changelog page
CHANGELOG_HTML = """
<html>
<body>
    <div class="card-item basic">
        <div class="flex-table">
            <div class="flex-table-item">
                <div class="item-title">학번</div><div class="item-data">60200001</div>
            </div>
            <div class="flex-table-item">
                <div class="item-title">학적상태</div><div class="item-data">재학</div>
            </div>
        </div>
    </div>
    <div class="card-item basic">
        <div class="data-title small">
            ... 누적학기 : <span style="color:red">총 2학기</span>
        </div>
        <div class="read-table">
            <table>
                <tbody>
                    <tr>
                        <td>2023</td><td>1학기</td><td>군입대휴학</td><td>2023-01-10</td><td>2025-02-28</td><td></td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@pytest.fixture
def mock_fetcher(monkeypatch):
    """Provides a StudentChangeLogFetcher with mocked network calls."""
    mock_session = MagicMock()
    fetcher = StudentChangeLogFetcher(session=mock_session)
    
    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: None)
    return fetcher

def test_student_changelog_fetcher_success(mock_fetcher, monkeypatch):
    """Tests that the fetcher correctly parses a valid HTML."""
    # Arrange
    monkeypatch.setattr(mock_fetcher, '_access_changelog_page', lambda: CHANGELOG_HTML)

    # Act
    result = mock_fetcher.fetch()

    # Assert
    assert result.success
    log = result.data
    assert isinstance(log, StudentChangeLog)
    assert log.academic_status.student_id == '60200001'
    assert log.academic_status.status == '재학'
    assert log.cumulative_leave_semesters == '총 2학기'
    assert len(log.change_log_list) == 1
    assert log.change_log_list[0].change_type == '군입대휴학'

def test_student_changelog_fetcher_parse_error(mock_fetcher, monkeypatch):
    """Tests that the fetcher returns a ParsingError for invalid HTML."""
    # Arrange
    monkeypatch.setattr(mock_fetcher, '_access_changelog_page', lambda: "<html></html>")

    # Act
    result = mock_fetcher.fetch()

    # Assert
    assert not result.success
    assert result.error_code == 'PARSING_ERROR'
    assert '학적 기본 정보 테이블을 찾을 수 없습니다' in result.error_message