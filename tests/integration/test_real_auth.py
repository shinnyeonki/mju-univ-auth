import os
import pytest
from dotenv import load_dotenv
from mju_univ_auth import StandardAuthenticator
from mju_univ_auth.config import SERVICES

load_dotenv()

USER_ID = os.getenv("MJU_ID")
USER_PW = os.getenv("MJU_PW")

requires_creds = pytest.mark.skipif(not USER_ID or not USER_PW, reason="MJU_ID and MJU_PW environment variables are not set.")

@requires_creds
@pytest.mark.parametrize("service_name", SERVICES.keys())
def test_real_login_for_all_services(service_name):
    """Tests real login for all supported services."""
    auth = StandardAuthenticator(user_id=USER_ID, user_pw=USER_PW)
    result = auth.login(service_name)

    assert result.success, f"Login failed for {service_name}: {result.error_message}"
    assert result.data is not None
