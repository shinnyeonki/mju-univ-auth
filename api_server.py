"""
MJU Univ Auth API Server
FastAPI를 사용하여 명지대학교 학생 인증 API를 제공합니다.
"""
import anyio
from fastapi import FastAPI, Request
from pydantic import BaseModel

from mju_univ_auth import MjuUnivAuth
from loguru import logger
from pathlib import Path
import time
from typing import Tuple
import uuid

# Setup log directory and Loguru configuration
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# --- 로그 포맷 정렬 설정 ---
# : <15  -> 왼쪽 정렬, 15칸 차지
# : >8   -> 오른쪽 정렬, 8칸 차지 (숫자에 적합)
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[ip]: <15} | "          # IP 주소 (15자리 고정)
    "{extra[student_id]: <8} | "  # 학번 (8자리 고정)
    "{extra[request_id]: <12} | "  # Req ID (req-xxxxxxxx 12자리)
    "{extra[method]: <5} | "       # Method (POST/GET 등 5자리)
    "{extra[path]: <30} | "        # Path (긴 경로 대비 30자리)
    "{extra[status]: <3} | "       # Status (200, 404 등 3자리)
    "{extra[elapsed]: >7.4f}s | "  # 소요시간 (우측 정렬)
    "{message}"
)
logger.add(str(LOG_DIR / "mju_api_{time:YYYY-MM-DD}.log"), rotation="1 day", retention="30 days", level="INFO", format=LOG_FORMAT)
import mju_univ_auth

# Limit blocking work to a single worker to avoid thread-unsafe access
thread_limiter = anyio.CapacityLimiter(1)

# --- FastAPI 앱 설정 ---
app = FastAPI(
    title="MJU Univ Auth API",
    description="명지대학교 학생 인증 및 정보 조회 API.",
    version=mju_univ_auth.__version__,
)

# --- 데이터 유효성 검사 ---
class AuthRequest(BaseModel):
    user_id: str
    user_pw: str

# --- API 엔드포인트 ---

@app.get("/", summary="API 상태 확인")
async def root():
    return {
        "name": "MJU Univ Auth API",
        "message": "MJU Univ Auth API is running.",
        "description": "/docs 에서 API 문서를 확인하세요.",
        "version": mju_univ_auth.__version__,
        }

def _map_result_to_level(result) -> Tuple[str, int, str]:
    """Map MjuUnivAuthResult -> (log_level, http_status, message)"""
    # Default mapping
    level = "INFO"
    status = 200
    message = ""

    try:
        # credentials invalid
        if result.request_succeeded and result.credentials_valid is False:
            level = "WARNING"
            status = 401
            message = f"Login Failed: {result.error_message}"
        elif not result.request_succeeded:
            level = "ERROR"
            status = 500
            message = f"Request failed: {result.error_message}"
        else:
            level = "INFO"
            status = 200
            # On success, keep more detailed message if available
            message = result.error_message if result.error_message else "OK"
    except Exception:
        level = "ERROR"
        status = 500
        message = "Unknown logging mapping error"

    return level, status, message


@app.post("/api/v1/student-card")
async def get_student_card(request: Request, req: AuthRequest):
    start = time.perf_counter()
    result = await anyio.to_thread.run_sync(
        lambda: MjuUnivAuth(user_id=req.user_id, user_pw=req.user_pw).get_student_card(),
        limiter=thread_limiter,
    )
    elapsed = time.perf_counter() - start
    # Logging
    level, status, message = _map_result_to_level(result)
    ip = request.client.host if request.client else "-"
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    logger.bind(ip=ip, student_id=req.user_id, request_id=request_id, method="POST", path="/api/v1/student-card", status=status, elapsed=elapsed).log(level, message)

    return {
        "request_succeeded": result.request_succeeded,
        "credentials_valid": result.credentials_valid,
        "data": result.data.to_dict() if result.data else None,
        "error_code": result.error_code.value if result.error_code else None,
        "error_message": result.error_message,
        "success": result.success
    }

@app.post("/api/v1/student-changelog")
async def get_student_changelog(request: Request, req: AuthRequest):
    start = time.perf_counter()
    result = await anyio.to_thread.run_sync(
        lambda: MjuUnivAuth(user_id=req.user_id, user_pw=req.user_pw).get_student_changelog(),
        limiter=thread_limiter,
    )
    elapsed = time.perf_counter() - start
    # Logging
    level, status, message = _map_result_to_level(result)
    ip = request.client.host if request.client else "-"
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    logger.bind(ip=ip, student_id=req.user_id, request_id=request_id, method="POST", path="/api/v1/student-changelog", status=status, elapsed=elapsed).log(level, message)

    return {
        "request_succeeded": result.request_succeeded,
        "credentials_valid": result.credentials_valid,
        "data": result.data.to_dict() if result.data else None,
        "error_code": result.error_code.value if result.error_code else None,
        "error_message": result.error_message,
        "success": result.success
    }