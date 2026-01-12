# from fastapi import FastAPI
# from app.routers import captcha

# app = FastAPI(
#     title="T-CURITY Backend API",
#     description="CAPTCHA verification API server",
#     version="1.0.0"
# )

# # Router 등록
# app.include_router(captcha.router)

# @app.get("/health")
# def health():
#     return {"status": "ok"}

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import Response
from app.endpoints.session_endpoints import router as session_router
from app.endpoints.phase_a_endpoints import router as phase_a_router
from app.endpoints.verify_endpoints import router as verify_router
from app.endpoints.health_endpoints import router as health_router
from app.core.blind_error_handler import blind_error_handler
from app.core.logging_config import (
    setup_logging, generate_trace_id, set_trace_id, get_trace_id, mask_ip
)
from app.core.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging
import time

# 로깅 설정 초기화
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

app = FastAPI(title="T-CURITY Backend API", version="1.0.0")


# =====================================================
# 요청/응답 로깅 미들웨어
# =====================================================
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # trace_id 생성 및 설정
    trace_id = generate_trace_id()
    set_trace_id(trace_id)
    
    start_time = time.time()
    
    # 요청 로깅 (민감 정보 마스킹)
    client_ip = request.client.host if request.client else "unknown"
    session_id = request.headers.get("X-Session-Id", "")
    
    logger.info(
        f"Request started",
        extra={
            "event": "request_start",
            "session_id": session_id,
            "client_ip": client_ip,
        }
    )
    
    # 요청 처리
    response: Response = await call_next(request)
    
    # 응답 로깅
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} {response.status_code}",
        extra={
            "event": "request_end",
            "result": "success" if response.status_code < 400 else "fail",
            "duration_ms": duration_ms,
            "session_id": session_id,
            "client_ip": client_ip,
        }
    )
    
    # trace_id 응답 헤더에 추가
    response.headers["X-Trace-Id"] = trace_id
    
    return response

# Rate Limiter 설정
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, blind_error_handler)

# BlindError 핸들러 등록 (4xx 에러 → 200 OK + VERIFICATION_FAILED)
app.add_exception_handler(HTTPException, blind_error_handler)

# 세션 생성
app.include_router(session_router, prefix="/api/v1/session")

# Phase A 문제 요청 → prefix는 captcha 하나만 사용해야 함
app.include_router(phase_a_router, prefix="/api/v1/captcha")

# 통합 verify (Phase A + Phase B)
app.include_router(verify_router, prefix="/api/v1/captcha")

# 헬스체크 (prefix 없음 - 루트에서 접근)
app.include_router(health_router)
