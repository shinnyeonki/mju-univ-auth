import pytest
from mju_univ_auth.infrastructure.parser import HTMLParser

# Sample HTML snippets for testing
LOGIN_PAGE_HTML = """
<html>
<body>
    <form id="signin-form" action="/sso/login.do">
        <input type="hidden" id="public-key" value="my-public-key" />
        <input type="hidden" id="c_r_t" value="my-csrf-token" />
    </form>
</body>
</html>
"""

LOGIN_PAGE_MISSING_ELEMENTS_HTML = """
<html>
<body>
    <form id="signin-form" action="/sso/login.do">
        <input type="hidden" id="public-key" value="my-public-key" />
    </form>
</body>
</html>
"""

JS_FORM_SUBMIT_HTML = """
<body onLoad="doLogin();">
    <form name="login" action="https://some-service.com/login" method="post">
        <input type="hidden" name="token" value="abc">
        <input type="hidden" name="user_id" value="123">
    </form>
    <script> function doLogin() { document.login.submit(); } </script>
</body>
"""

JS_REDIRECT_HTML = """
<script>
    location.href = '/redirect/path';
</script>
"""

ERROR_MSG_HTML_ALERT = """
<script>
    alert('아이디 또는 비밀번호가 일치하지 않습니다.');
</script>
"""

ERROR_MSG_HTML_VAR = """
<script>
    var errorMsg = "This is an error.";
</script>
"""

STUDENT_CARD_HTML = """
<div>
    <img src="data:image/jpeg;base64,my-photo-data" />
    <div class="flex-table-item">
        <div class="item-title">학번</div>
        <div class="item-data"><input value="60200001" /></div>
    </div>
    <div class="flex-table-item">
        <div class="item-title">한글성명</div>
        <div class="item-data">홍길동</div>
    </div>
    <div class="flex-table-item">
        <div class="item-title">E-Mail</div>
        <div class="item-data"><input name="email" value="test@mju.ac.kr" /></div>
    </div>
</div>
"""

CHANGE_LOG_HTML = """
<div>
    <div class="flex-table-item">
        <div class="item-title">학번</div>
        <div class="item-data">60200001</div>
    </div>
    <div class="flex-table-item">
        <div class="item-title">학적상태</div>
        <div class="item-data">재학</div>
    </div>
</div>
"""

CSRF_HTML_META = '<meta name="_csrf" content="meta-token" />'
CSRF_HTML_INPUT = '<input type="hidden" name="_csrf" value="input-token" />'


class TestHTMLParser:
    @pytest.mark.parametrize("html, expected", [
        (CSRF_HTML_META, "meta-token"),
        (CSRF_HTML_INPUT, "input-token"),
        ('<html></html>', None),
    ])
    def test_extract_csrf_token(self, html, expected):
        assert HTMLParser.extract_csrf_token(html) == expected

    def test_extract_login_page_data_success(self):
        key, csrf, action = HTMLParser.extract_login_page_data(LOGIN_PAGE_HTML)
        assert key == "my-public-key"
        assert csrf == "my-csrf-token"
        assert action == "/sso/login.do"

    def test_extract_login_page_data_failure(self):
        key, csrf, action = HTMLParser.extract_login_page_data(LOGIN_PAGE_MISSING_ELEMENTS_HTML)
        assert key == "my-public-key"
        assert csrf is None
        assert action == "/sso/login.do"

    def test_extract_form_data(self):
        action, data = HTMLParser.extract_form_data(JS_FORM_SUBMIT_HTML)
        assert action == "https://some-service.com/login"
        assert data == {"token": "abc", "user_id": "123"}

    @pytest.mark.parametrize("html, expected", [
        (ERROR_MSG_HTML_ALERT, "아이디 또는 비밀번호가 일치하지 않습니다."),
        (ERROR_MSG_HTML_VAR, "This is an error."),
        ("<html></html>", None),
    ])
    def test_extract_error_message(self, html, expected):
        assert HTMLParser.extract_error_message(html) == expected

    def test_extract_js_redirect(self):
        assert HTMLParser.extract_js_redirect(JS_REDIRECT_HTML) == "/redirect/path"

    def test_boolean_flags(self):
        assert HTMLParser.has_js_form_submit(JS_FORM_SUBMIT_HTML) is True
        assert HTMLParser.has_signin_form('<div id="signin-form">...<div id="input-password">') is True
        assert HTMLParser.has_logout_button("<a>로그아웃</a>") is True
        assert HTMLParser.has_logout_button("<a>logout</a>") is True

    def test_parse_student_card_fields(self):
        fields = HTMLParser.parse_student_card_fields(STUDENT_CARD_HTML)
        assert fields['photo_base64'] == 'my-photo-data'
        assert fields['학번'] == '60200001'
        assert fields['한글성명'] == '홍길동'
        assert fields['email'] == 'test@mju.ac.kr'

    def test_parse_change_log_fields(self):
        fields = HTMLParser.parse_change_log_fields(CHANGE_LOG_HTML)
        assert fields['학번'] == '60200001'
        assert fields['학적상태'] == '재학'
