import pytest

from mju_univ_auth import (
    StudentChangeLogFetcher,
    StudentChangeLog,
    ParsingError,
    NetworkError,
    ErrorCode,
)


class DummySession:
    def __init__(self):
        self._get_response_text = ''
        self._post_response_text = ''

    def get(self, url, timeout=None):
        return type('R', (), {'text': self._get_response_text, 'url': url, 'status_code': 200})()

    def post(self, url, data=None, headers=None, timeout=None):
        return type('R', (), {'text': self._post_response_text, 'url': url, 'status_code': 200})()


@pytest.fixture
def dummy_session():
    return DummySession()


def test_student_changelog_fetcher_success(monkeypatch, dummy_session):
    fetcher = StudentChangeLogFetcher(session=dummy_session)

    # 메서드를 스텁합니다
    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: setattr(fetcher, '_csrf_token', 'token'))

    sample_html = '<div class="flex-table-item"><div class="item-title">학번</div><div class="item-data">20200001</div></div>'
    monkeypatch.setattr(fetcher, '_access_changelog_page', lambda: sample_html)

    # 파싱 결과를 모의로 만듭니다
    sample_changelog = StudentChangeLog(student_id='20200001', name='홍길동', status='재학', grade='1', completed_semesters='1', department='컴퓨터')
    monkeypatch.setattr(fetcher, '_parse_changelog', lambda html: sample_changelog)

    result = fetcher.fetch()

    assert result.success
    assert result.data.student_id == '20200001'


def test_student_changelog_fetcher_parse_error(monkeypatch, dummy_session):
    fetcher = StudentChangeLogFetcher(session=dummy_session)

    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: setattr(fetcher, '_csrf_token', 'token'))
    monkeypatch.setattr(fetcher, '_access_changelog_page', lambda: '<html></html>')

    # _parse_changelog가 ParsingError를 발생시키도록 모의합니다
    def raising_parse(html):
        raise ParsingError('Parsing failed', field='student_id')

    monkeypatch.setattr(fetcher, '_parse_changelog', raising_parse)

    result = fetcher.fetch()

    assert not result.request_succeeded
    assert result.error_code == ErrorCode.PARSING_ERROR


def test_student_changelog_fetcher_network_error(monkeypatch, dummy_session):
    fetcher = StudentChangeLogFetcher(session=dummy_session)

    def raising_get_csrf():
        raise NetworkError('Network issue', url='https://msi.mju.ac.kr')

    monkeypatch.setattr(fetcher, '_get_csrf_token', raising_get_csrf)

    result = fetcher.fetch()

    assert not result.request_succeeded
    assert result.credentials_valid is None
    assert result.error_code == ErrorCode.NETWORK_ERROR
