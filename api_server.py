"""
MJU Univ Auth API Server (v2)
FastAPI를 사용하여 명지대학교 학생 인증 API를 제공합니다.
저수준 컴포넌트(Authenticator, Fetcher)를 사용하여 세션 관리 및 데이터 조회의 유연성을 확보합니다.
"""
import time
import uuid
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, TypeVar, Generic
from importlib.metadata import version

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger
from requests import Session

from mju_univ_auth import ErrorCode
from mju_univ_auth import (
    NetworkError,
    ParsingError,
    InvalidCredentialsError,
    SessionExpiredError,
    SessionNotExistError,
    AlreadyLoggedInError,
    ServiceNotFoundError,
    InvalidServiceUsageError
)


from mju_univ_auth import (
    StandardAuthenticator,
    StudentBasicInfoFetcher,
    StudentChangeLogFetcher,
    StudentCardFetcher,
    MjuUnivAuthError,
    StudentBasicInfo,
    StudentCard,
    StudentChangeLog,
)

# 1. --- 로깅 설정 ---
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{extra[ip]: <15} | "
    "{extra[student_id]: <8} | "
    "{extra[request_id]: <12} | "
    "{extra[method]: <5} | "
    "{extra[path]: <30} | "
    "{extra[status]: <3} | "
    "{extra[elapsed]: >7.4f}s | "
    "{message}"
)
logger.add(
    str(LOG_DIR / "mju_api_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="30 years",
    level="INFO",
    format=LOG_FORMAT,
)


# 2. --- FastAPI 앱 및 Pydantic 모델 ---
try:
    MJU_AUTH_VERSION = version('mju_univ_auth')
except Exception:
    MJU_AUTH_VERSION = "unknown"

app = FastAPI(
    title="MJU Univ Auth API",
    description="명지대학교 학생 인증 및 정보 조회 API.",
    version=MJU_AUTH_VERSION,
)

class AuthRequest(BaseModel):
    user_id: str
    user_pw: str

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    request_succeeded: bool = True
    credentials_valid: bool = True
    data: T
    error_code: Optional[ErrorCode] = None
    error_message: str = ""
    success: bool = True

class ErrorResponse(BaseModel):
    request_succeeded: bool
    credentials_valid: bool
    data: Optional[Any] = None
    error_code: str
    error_message: str
    success: bool = False


# 3. --- 핵심 로직 클래스 ---

class Config:
    SESSION_TIMEOUT_SECONDS = 1800  # 30분
    DATA_CACHE_TIMEOUT_SECONDS = 1200  # 20분

class PasswordManager:
    """비밀번호 해싱 및 검증을 담당합니다."""
    @staticmethod
    def hash_password(password: str) -> str:
        """SHA256을 사용하여 비밀번호를 해싱합니다."""
        return hashlib.sha256(password.encode()).hexdigest()

class SessionCache:
    """
    스레드 안전 인메모리 세션 캐시.
    사용자 ID별로 (세션, 비밀번호 해시, 타임스탬프)를 저장합니다.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_user_lock(self, user_id: str) -> threading.Lock:
        """사용자 ID에 대한 Lock을 가져오거나 생성하여 반환합니다."""
        with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = threading.Lock()
            return self._locks[user_id]

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        """캐시에서 항목을 가져옵니다."""
        return self._cache.get(user_id)

    def set(self, user_id: str, session: Session, password_hash: str):
        """캐시에 세션과 관련 정보를 저장합니다."""
        self._cache[user_id] = {
            "session": session,
            "password_hash": password_hash,
            "timestamp": datetime.now(),
        }

    def invalidate(self, user_id: str):
        """특정 사용자의 캐시를 무효화합니다."""
        if user_id in self._cache:
            del self._cache[user_id]

    def is_valid(self, entry: Optional[Dict[str, Any]], password_hash: str) -> bool:
        """캐시된 항목이 유효한지 (비밀번호 일치, 타임아웃 전) 확인합니다."""
        if not entry:
            return False
        
        if entry["password_hash"] != password_hash:
            return False
            
        age = datetime.now() - entry["timestamp"]
        if age > timedelta(seconds=Config.SESSION_TIMEOUT_SECONDS):
            return False
            
        return True

    def get_lock(self, user_id: str) -> threading.Lock:
        """특정 사용자에 대한 동기화 Lock을 반환합니다."""
        return self._get_user_lock(user_id)

class DataCache:
    """
    스레드 안전한 인메모리 데이터 캐시.
    사용자 ID별, 데이터 타입별로 데이터를 저장하여 특정 사용자의 전체 캐시를 쉽게 무효화할 수 있습니다.
    """
    def __init__(self):
        self._cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def _get_user_lock(self, user_id: str) -> threading.Lock:
        with self._global_lock:
            if user_id not in self._locks:
                self._locks[user_id] = threading.Lock()
            return self._locks[user_id]

    def get(self, user_id: str, data_type: str) -> Optional[Dict[str, Any]]:
        """사용자 ID와 데이터 타입으로 캐시된 항목을 가져옵니다."""
        user_cache = self._cache.get(user_id)
        if user_cache:
            return user_cache.get(data_type)
        return None

    def set(self, user_id: str, data_type: str, data: Any, password_hash: str):
        """캐시에 데이터를 저장합니다."""
        if user_id not in self._cache:
            self._cache[user_id] = {}
        self._cache[user_id][data_type] = {
            "data": data,
            "password_hash": password_hash,
            "timestamp": datetime.now(),
        }

    def invalidate_user(self, user_id: str):
        """특정 사용자의 모든 데이터 캐시를 무효화합니다."""
        if user_id in self._cache:
            del self._cache[user_id]

    def is_valid(self, entry: Optional[Dict[str, Any]], password_hash: str) -> bool:
        if not entry:
            return False
        
        if entry["password_hash"] != password_hash:
            return False
            
        age = datetime.now() - entry["timestamp"]
        if age > timedelta(seconds=Config.DATA_CACHE_TIMEOUT_SECONDS):
            return False
            
        return True

    def get_lock(self, user_id: str) -> threading.Lock:
        return self._get_user_lock(user_id)

class MjuAuthService:
    """
    인증 및 데이터 조회를 위한 핵심 서비스.
    세션 및 데이터 캐싱과 저수준 컴포넌트 호출을 관리합니다.
    """
    def __init__(self, session_cache: SessionCache, data_cache: DataCache):
        self._session_cache = session_cache
        self._data_cache = data_cache

    def _raise_from_result(self, result):
        """결과 객체를 기반으로 특정 예외를 발생시킵니다."""
        if result.success:
            return

        error_message = result.error_message
        error_code = getattr(result, 'error_code', None)

        if error_code == ErrorCode.INVALID_CREDENTIALS_ERROR:
            raise InvalidCredentialsError(error_message)
        elif error_code == ErrorCode.NETWORK_ERROR:
            raise NetworkError(error_message)
        elif error_code == ErrorCode.PARSING_ERROR:
            raise ParsingError(error_message)
        elif error_code == ErrorCode.SESSION_EXPIRED_ERROR:
            raise SessionExpiredError(error_message)
        elif error_code == ErrorCode.SESSION_NOT_EXIST_ERROR:
            raise SessionNotExistError(error_message)
        elif error_code == ErrorCode.ALREADY_LOGGED_IN_ERROR:
            raise AlreadyLoggedInError(error_message)
        elif error_code == ErrorCode.SERVICE_NOT_FOUND_ERROR:
            raise ServiceNotFoundError(error_message)
        elif error_code == ErrorCode.INVALID_SERVICE_USAGE_ERROR:
            raise InvalidServiceUsageError(error_message)
        else:
            # 알려지지 않은 오류 코드나 오류 코드가 없는 경우에 대한 폴백
            raise MjuUnivAuthError(error_message)

    def _get_valid_session(self, user_id: str, user_pw: str) -> Session:
        """
        유효한 세션을 가져오거나, 없으면 새로 생성하여 반환합니다.
        스레드 안전성을 보장합니다.
        """
        password_hash = PasswordManager.hash_password(user_pw)
        
        with self._session_cache.get_lock(user_id):
            cached_entry = self._session_cache.get(user_id)

            if self._session_cache.is_valid(cached_entry, password_hash):
                return cached_entry["session"]

            self._session_cache.invalidate(user_id)
            
            authenticator = StandardAuthenticator(user_id=user_id, user_pw=user_pw)
            login_result = authenticator.login(service='msi')

            if not login_result.success:
                # 인증 실패 시, 해당 사용자의 모든 데이터 캐시를 삭제합니다.
                if getattr(login_result, 'error_code', None) == ErrorCode.INVALID_CREDENTIALS_ERROR:
                    self._data_cache.invalidate_user(user_id)
                self._raise_from_result(login_result)
            
            session = authenticator.session
            self._session_cache.set(user_id, session, password_hash)
            return session

    def _fetch_with_retry(self, user_id: str, password: str, fetcher_cls, **kwargs):
        """데이터 조회를 재시도 로직과 함께 수행합니다."""
        try:
            session = self._get_valid_session(user_id, password)
            fetcher = fetcher_cls(session=session, **kwargs)
            result = fetcher.fetch()

            if result.success:
                return result.data

            # 세션 만료 등으로 조회가 실패했을 수 있으므로 세션을 무효화하고 재시도합니다.
            self._session_cache.invalidate(user_id)
            session = self._get_valid_session(user_id, password)
            fetcher = fetcher_cls(session=session, **kwargs)
            result = fetcher.fetch()

            if result.success:
                return result.data
            
            self._raise_from_result(result)

        except MjuUnivAuthError as e:
            raise e
    
    def get_student_basicinfo(self, user_id: str, user_pw: str) -> StudentBasicInfo:
        """학적기본정보를 조회하고 결과를 캐싱합니다."""
        password_hash = PasswordManager.hash_password(user_pw)
        data_type = "student-basicinfo"

        with self._data_cache.get_lock(user_id):
            cached_entry = self._data_cache.get(user_id, data_type)
            if self._data_cache.is_valid(cached_entry, password_hash):
                return cached_entry["data"]

            data = self._fetch_with_retry(
                user_id, user_pw, StudentBasicInfoFetcher
            )
            self._data_cache.set(user_id, data_type, data, password_hash)
            return data

    def get_student_changelog(self, user_id: str, user_pw: str) -> StudentChangeLog:
        """학적변동내역을 조회하고 결과를 캐싱합니다."""
        password_hash = PasswordManager.hash_password(user_pw)
        data_type = "student-changelog"

        with self._data_cache.get_lock(user_id):
            cached_entry = self._data_cache.get(user_id, data_type)
            if self._data_cache.is_valid(cached_entry, password_hash):
                return cached_entry["data"]

            data = self._fetch_with_retry(
                user_id, user_pw, StudentChangeLogFetcher
            )
            self._data_cache.set(user_id, data_type, data, password_hash)
            return data

    def get_student_card(self, user_id: str, user_pw: str) -> StudentCard:
        """학생증 정보를 조회하고 결과를 캐싱합니다."""
        password_hash = PasswordManager.hash_password(user_pw)
        data_type = "student-card"

        with self._data_cache.get_lock(user_id):
            cached_entry = self._data_cache.get(user_id, data_type)
            if self._data_cache.is_valid(cached_entry, password_hash):
                return cached_entry["data"]

            data = self._fetch_with_retry(
                user_id, user_pw, StudentCardFetcher, user_pw=user_pw
            )
            self._data_cache.set(user_id, data_type, data, password_hash)
            return data

# 전역 서비스 및 캐시 인스턴스 생성
session_cache = SessionCache()
data_cache = DataCache()
auth_service = MjuAuthService(session_cache, data_cache)


# 4. --- API 미들웨어 ---

ERROR_MAPPING: Dict[Exception, Tuple[int, ErrorCode, bool]] = {
    InvalidCredentialsError: (status.HTTP_401_UNAUTHORIZED, ErrorCode.INVALID_CREDENTIALS_ERROR, False),
    SessionNotExistError: (status.HTTP_401_UNAUTHORIZED, ErrorCode.SESSION_NOT_EXIST_ERROR, False),
    SessionExpiredError: (status.HTTP_401_UNAUTHORIZED, ErrorCode.SESSION_EXPIRED_ERROR, False),
    InvalidServiceUsageError: (status.HTTP_403_FORBIDDEN, ErrorCode.INVALID_SERVICE_USAGE_ERROR, True),
    AlreadyLoggedInError: (status.HTTP_409_CONFLICT, ErrorCode.ALREADY_LOGGED_IN_ERROR, True),
    ServiceNotFoundError: (status.HTTP_422_UNPROCESSABLE_CONTENT, ErrorCode.SERVICE_NOT_FOUND_ERROR, True),
    NetworkError: (status.HTTP_502_BAD_GATEWAY, ErrorCode.NETWORK_ERROR, True),
    ParsingError: (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.PARSING_ERROR, True),
    MjuUnivAuthError: (status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.UNKNOWN_ERROR, False),
}

@app.middleware("http")
async def api_middleware(request: Request, call_next) -> JSONResponse:
    """
    모든 API 요청을 가로채 로깅, 예외 처리, 응답 형식화를 수행합니다.
    """
    start_time = time.perf_counter()
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    student_id = "-"
    
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    log_level: str = "ERROR"
    log_message: str = "Internal server error"

    try:
        if request.method == "POST" and "/api/" in request.url.path:
            try:
                body = await request.json()
                student_id = body.get("user_id", "-")
            except Exception:
                student_id = "invalid_json"

        response = await call_next(request)
        
        status_code = response.status_code
        if status.HTTP_200_OK <= status_code < status.HTTP_300_MULTIPLE_CHOICES:
            log_level = "INFO"
            log_message = "OK"
        else:
            log_level = "WARNING"
            log_message = "Request validation error or not found"
            if hasattr(response, "body"):
                try:
                    log_message = response.body.decode()
                except Exception:
                    pass

        return response

    except MjuUnivAuthError as e:
        status_code, error_code, credentials_valid = ERROR_MAPPING[type(e)]

        log_message = str(e)
        log_level = "WARNING" if status_code < 500 else "ERROR"
        
        response_data = {
            "request_succeeded": False,
            "credentials_valid": credentials_valid,
            "data": None,
            "error_code": error_code.value,
            "error_message": log_message,
            "success": False,
        }
        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        log_message = f"Unexpected error: {str(e)}"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        log_level = "ERROR"
        
        response_data = {
            "request_succeeded": False,
            "credentials_valid": False,
            "data": None,
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "Internal server error.",
            "success": False,
        }
        return JSONResponse(content=response_data, status_code=status_code)

    finally:
        elapsed = time.perf_counter() - start_time
        logger.bind(
            ip=request.client.host if request.client else "-",
            student_id=student_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=status_code,
            elapsed=elapsed,
        ).log(log_level, log_message)


# 5. --- API 엔드포인트 ---

@app.get("/", summary="API 상태 확인", include_in_schema=True)
async def root():
    return {
        "name": "MJU Univ Auth API",
        "version": MJU_AUTH_VERSION,
        "description": "명지대학교 학생 인증 및 정보 조회 API. /docs 에서 문서를 확인하세요.",
    }


@app.post(
    "/api/v1/student-basicinfo",
    summary="학생 기본 정보 조회",
    response_model=SuccessResponse[StudentBasicInfo],
    responses={
        401: {"model": ErrorResponse, "description": "INVALID_CREDENTIALS_ERROR 인증 실패 (자격 증명 오류, 세션 만료 등)"},
        409: {"model": ErrorResponse, "description": "로그인 상태에서 재 로그인등 서버 상태와 충돌 요청"},
        422: {"model": ErrorResponse, "description": "SERVICE_NOT_FOUND_ERROR, 처리 불가능한 요청 (잘못된 서비스 이름) 내부 로직 문제"},
        500: {"model": ErrorResponse, "description": "PARSING_ERROR, UNKNOWN_ERROR 서버 내부 오류 (파싱 실패 등)"},
        502: {"model": ErrorResponse, "description": "NETWORK_ERROR 게이트웨이 오류 (업스트림 네트워크 문제)"},
    }
)
async def get_student_basicinfo(req: AuthRequest):
    """
    사용자 인증 후 학적변동내역을 조회합니다.
    - **user_id**: 학번
    - **user_pw**: myiweb 비밀번호
    """
    data = auth_service.get_student_basicinfo(req.user_id, req.user_pw)
    return {"data": data}


@app.post(
    "/api/v1/student-changelog",
    summary="학적변동내역 조회",
    response_model=SuccessResponse[StudentChangeLog],
    responses={
        401: {"model": ErrorResponse, "description": "INVALID_CREDENTIALS_ERROR 인증 실패 (자격 증명 오류, 세션 만료 등)"},
        409: {"model": ErrorResponse, "description": "로그인 상태에서 재 로그인등 서버 상태와 충돌 요청"},
        422: {"model": ErrorResponse, "description": "SERVICE_NOT_FOUND_ERROR, 처리 불가능한 요청 (잘못된 서비스 이름) 내부 로직 문제"},
        500: {"model": ErrorResponse, "description": "PARSING_ERROR, UNKNOWN_ERROR 서버 내부 오류 (파싱 실패 등)"},
        502: {"model": ErrorResponse, "description": "NETWORK_ERROR 게이트웨이 오류 (업스트림 네트워크 문제)"},
    }
)
async def get_student_changelog(req: AuthRequest):
    """
    사용자 인증 후 학적변동내역을 조회합니다.
    - **user_id**: 학번
    - **user_pw**: myiweb 비밀번호
    """
    data = auth_service.get_student_changelog(req.user_id, req.user_pw)
    return {"data": data}

@app.post(
    "/api/v1/student-card",
    summary="학생증 정보 조회",
    response_model=SuccessResponse[StudentCard],
    responses={
        401: {"model": ErrorResponse, "description": "INVALID_CREDENTIALS_ERROR 인증 실패 (자격 증명 오류, 세션 만료 등)"},
        409: {"model": ErrorResponse, "description": "로그인 상태에서 재 로그인등 서버 상태와 충돌 요청"},
        422: {"model": ErrorResponse, "description": "SERVICE_NOT_FOUND_ERROR, 처리 불가능한 요청 (잘못된 서비스 이름) 내부 로직 문제"},
        500: {"model": ErrorResponse, "description": "PARSING_ERROR, UNKNOWN_ERROR 서버 내부 오류 (파싱 실패 등)"},
        502: {"model": ErrorResponse, "description": "NETWORK_ERROR 게이트웨이 오류 (업스트림 네트워크 문제)"},
    }
)
async def get_student_card(req: AuthRequest):
    """
    사용자 인증 후 학생증 정보를 조회합니다.
    - **user_id**: 학번
    - **user_pw**: myiweb 비밀번호
    """
    data = auth_service.get_student_card(req.user_id, req.user_pw)
    return {"data": data}


# 6. --- 서버 실행 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
