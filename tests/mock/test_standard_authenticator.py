import pytest
import requests
import requests_mock
from mju_univ_auth.authenticator.standard_authenticator import StandardAuthenticator
from mju_univ_auth.config import SERVICES
from mju_univ_auth.exceptions import ParsingError, InvalidCredentialsError, NetworkError

# A minimal valid login page HTML structure
LOGIN_PAGE_HTML = """
<html><body>
    <form id="signin-form" action="/sso/process/login.do">
        <input type="hidden" id="public-key" value="dummypublickey" />
        <input type="hidden" id="c_r_t" value="dummycsrftoken" />
    </form>
</body></html>
"""

# A minimal malformed login page (missing public key)
MALFORMED_LOGIN_PAGE_HTML = """
<html><body>
    <form id="signin-form" action="/sso/process/login.do">
        <input type="hidden" id="c_r_t" value="dummycsrftoken" />
    </form>
</body></html>
"""

# A minimal redirect page that submits a form via JS
REDIRECT_FORM_HTML = """
<html><body onLoad="document.login.submit();">
    <form name="login" action="{final_url}" method="post">
        <input type="hidden" name="token" value="finaltoken">
    </form>
</body></html>
"""

# A minimal final page indicating success (e.g., has a logout button)
FINAL_PAGE_HTML = "<html><body><a>로그아웃</a></body></html>"

# A page indicating invalid credentials
INVALID_CRED_HTML = """
<html><body>
    <form id="signin-form"></form>
    <script>alert('ID 또는 비밀번호가 일치하지 않습니다.');</script>
</body></html>
"""

@pytest.fixture
def auth():
    """Provides a StandardAuthenticator instance."""
    return StandardAuthenticator(user_id="testuser", user_pw="testpass")

@pytest.fixture(autouse=True)
def mock_crypto(monkeypatch):
    """Mocks the cryptography functions to avoid actual encryption."""
    monkeypatch.setattr(
        'mju_univ_auth.authenticator.standard_authenticator.generate_session_key',
        lambda length: {'keyStr': 'dummy_key_str', 'key': b'dummy_key', 'iv': b'dummy_iv'}
    )
    monkeypatch.setattr(
        'mju_univ_auth.authenticator.standard_authenticator.encrypt_with_rsa',
        lambda data, public_key: "encrypted_rsa_data"
    )
    monkeypatch.setattr(
        'mju_univ_auth.authenticator.standard_authenticator.encrypt_with_aes',
        lambda plain_text, key_info: "encrypted_aes_data"
    )

def test_login_success(auth, requests_mock):
    """Tests a successful login flow with redirects."""
    service = 'msi'
    service_config = SERVICES[service]
    sso_host = "https://sso.mju.ac.kr"
    
    # 1. Initial GET to the login page
    requests_mock.get(service_config.auth_url, text=LOGIN_PAGE_HTML)
    
    # 2. POST to the SSO login processing URL
    requests_mock.post(f"{sso_host}/sso/process/login.do", text=REDIRECT_FORM_HTML.format(final_url=service_config.final_url))
    
    # 3. POST by the redirect form to the final service URL
    requests_mock.post(service_config.final_url, text=FINAL_PAGE_HTML)

    result = auth.login(service)

    assert result.success
    assert result.data is not None
    assert requests_mock.call_count == 3

def test_login_failure_invalid_credentials(auth, requests_mock):
    """Tests a login failure due to invalid credentials."""
    service = 'msi'
    service_config = SERVICES[service]
    sso_host = "https://sso.mju.ac.kr"

    # 1. Initial GET
    requests_mock.get(service_config.auth_url, text=LOGIN_PAGE_HTML)
    
    # 2. POST returns an error page
    requests_mock.post(f"{sso_host}/sso/process/login.do", text=INVALID_CRED_HTML)

    result = auth.login(service)

    assert not result.success
    assert not result.credentials_valid
    assert "ID 또는 비밀번호" in result.error_message

def test_login_failure_parsing_error(auth, requests_mock):
    """Tests a login failure due to a malformed login page."""
    service = 'msi'
    service_config = SERVICES[service]

    # Return a malformed page
    requests_mock.get(service_config.auth_url, text=MALFORMED_LOGIN_PAGE_HTML)

    result = auth.login(service)

    assert not result.success
    assert "공개키(public-key)를 찾을 수 없습니다." in result.error_message

def test_login_failure_network_error(auth, requests_mock):
    """Tests a login failure due to a network error."""
    service = 'msi'
    service_config = SERVICES[service]

    # Mock a network error
    requests_mock.get(service_config.auth_url, exc=requests.exceptions.ConnectTimeout)

    result = auth.login(service)

    assert not result.success
    assert "로그인 페이지 접속 실패" in result.error_message

def test_is_session_valid_success(auth, requests_mock):
    """Tests when the session is valid."""
    service = 'msi'
    service_config = SERVICES[service]
    
    # Set a dummy session on the authenticator
    auth._session = requests.Session()
    
    requests_mock.get(service_config.final_url, text=FINAL_PAGE_HTML)
    
    assert auth.is_session_valid(service) is True

def test_is_session_valid_failure(auth, requests_mock):
    """Tests when the session is invalid (login form is shown)."""
    service = 'msi'
    service_config = SERVICES[service]
    
    auth._session = requests.Session()
    
    # The login page itself is a sign of an invalid session
    requests_mock.get(service_config.final_url, text=LOGIN_PAGE_HTML)
    
    assert auth.is_session_valid(service) is False


def test_is_session_valid_no_session(auth):
    """Tests when no session exists on the authenticator."""
    assert auth.is_session_valid('msi') is False