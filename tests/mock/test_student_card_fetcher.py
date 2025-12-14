import pytest
import requests

from mju_univ_auth import (
    StudentCardFetcher,
    StudentCard,
    PageParsingError,
    NetworkError,
    InvalidCredentialsError,
    ErrorCode,
)


class DummyResponse:
    def __init__(self, text="", url="https://msi.mju.ac.kr/servlet/security/MySecurityStart"):
        self.text = text
        self.url = url
        self.status_code = 200


class DummySession:
    def __init__(self):
        self.last_post = None
        self.last_get = None

    def post(self, url, data=None, headers=None, timeout=None):
        self.last_post = (url, data, headers)
        return DummyResponse(text=getattr(self, '_post_response_text', ''), url=url)

    def get(self, url, timeout=None):
        self.last_get = (url,)
        return DummyResponse(text=getattr(self, '_get_response_text', ''), url=url)


@pytest.fixture
def dummy_session():
    return DummySession()


def test_student_card_fetcher_success(monkeypatch, dummy_session):
    # fetcher가 더미 세션을 사용하도록 합니다
    fetcher = StudentCardFetcher(session=dummy_session, user_pw='pw')

    # _get_csrf_token이 네트워크 호출 없이 토큰을 설정하도록 모의합니다
    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: setattr(fetcher, '_csrf_token', 'token123'))

    # 파싱할 필드가 포함된 페이지(HTML)를 반환하도록 합니다
    sample_html = '<div class="flex-table-item"><div class="item-title">학번</div><div class="item-data">20200001</div></div>'
    monkeypatch.setattr(fetcher, '_access_student_card_page', lambda: sample_html)

    # 실제 HTML 파싱 로직을 호출해 필드 값을 만드는 흐름을 건너뛰고
    # _parse_student_card를 스텁하여 간단히 StudentCard를 반환하도록 합니다
    expected_card = StudentCard(student_id='20200001', name_korean='홍길동')
    monkeypatch.setattr(fetcher, '_parse_student_card', lambda html: expected_card)

    result = fetcher.fetch()

    assert result.success
    assert result.data.student_id == '20200001'
    assert isinstance(result.data, StudentCard)


def test_student_card_fetcher_parse_error(monkeypatch, dummy_session):
    fetcher = StudentCardFetcher(session=dummy_session, user_pw='pw')

    # 페이지 접근이 정상인 것처럼 모의합니다
    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: setattr(fetcher, '_csrf_token', 'token123'))
    monkeypatch.setattr(fetcher, '_access_student_card_page', lambda: '<html></html>')

    # 파싱 시 PageParsingError가 발생하는 상황을 모의합니다
    def raising_parse(html):
        raise PageParsingError('Unable to parse', field='student_id')

    monkeypatch.setattr(fetcher, '_parse_student_card', raising_parse)

    result = fetcher.fetch()

    assert not result.request_succeeded
    assert result.credentials_valid is True
    assert result.error_code == ErrorCode.PARSE_ERROR


def test_student_card_fetcher_network_error(monkeypatch, dummy_session):
    fetcher = StudentCardFetcher(session=dummy_session, user_pw='pw')

    # _get_csrf_token이 NetworkError를 발생시키도록 모의합니다
    def raising_get_csrf():
        raise NetworkError('Unable to reach site', url='https://msi.mju.ac.kr')

    monkeypatch.setattr(fetcher, '_get_csrf_token', raising_get_csrf)

    result = fetcher.fetch()

    assert not result.request_succeeded
    assert result.credentials_valid is None
    assert result.error_code == ErrorCode.NETWORK_ERROR


def test_student_card_fetcher_invalid_second_password(monkeypatch, dummy_session):
    # _is_password_required가 True를 반환하고 _submit_password가 여전히 비밀번호 필요 HTML을 반환하는 흐름을 만듭니다
    fetcher = StudentCardFetcher(session=dummy_session, user_pw='wrong_pw')

    monkeypatch.setattr(fetcher, '_get_csrf_token', lambda: setattr(fetcher, '_csrf_token', 'x'))
    monkeypatch.setattr(fetcher, '_access_student_card_page', lambda: '<html>tfpassword</html>')
    monkeypatch.setattr(fetcher, '_is_password_required', lambda html: True)

    # _submit_password가 여전히 비밀번호 필요를 나타내는 HTML을 반환하도록 설정합니다
    monkeypatch.setattr(fetcher, '_submit_password', lambda html: '<html>tfpassword</html>')

    result = fetcher.fetch()

    assert result.request_succeeded
    assert result.credentials_valid is False
    assert result.error_code == ErrorCode.AUTH_FAILED
    assert '2차 비밀번호' in result.error_message