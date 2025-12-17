import os
import pytest
from dotenv import load_dotenv
from mju_univ_auth import MjuUnivAuth

load_dotenv()

USER_ID = os.getenv("MJU_ID")
USER_PW = os.getenv("MJU_PW")

requires_creds = pytest.mark.skipif(not USER_ID or not USER_PW, reason="MJU_ID and MJU_PW environment variables are not set.")

@requires_creds
def test_real_get_student_card():
    """Tests fetching the student card with real credentials."""
    auth = MjuUnivAuth(user_id=USER_ID, user_pw=USER_PW)
    auth.login('msi')
    result = auth.get_student_card()

    assert result.success, f"Failed to get student card: {result.error_message}"
    assert result.data is not None
    assert result.data.student_profile.student_id == USER_ID

@requires_creds
def test_real_get_student_changelog():
    """Tests fetching the student changelog with real credentials."""
    auth = MjuUnivAuth(user_id=USER_ID, user_pw=USER_PW)
    auth.login('msi')
    result = auth.get_student_changelog()

    assert result.success, f"Failed to get student changelog: {result.error_message}"
    assert result.data is not None
    assert result.data.academic_status.student_id == USER_ID

@requires_creds
def test_real_login_chaining():
    """Tests chaining login and fetch methods."""
    auth = MjuUnivAuth(user_id=USER_ID, user_pw=USER_PW)
    result = auth.login('msi').get_student_card()

    assert result.success, f"Failed to get student card via chaining: {result.error_message}"
    assert result.data is not None
    assert result.data.student_profile.student_id == USER_ID