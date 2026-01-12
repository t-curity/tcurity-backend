# app/core/blind_error_handler.py
"""
BlindError 응답 로직

보안 강화를 위해 4xx 에러를 200 OK + success: false로 변환합니다.
- 5xx 에러는 Blind 처리하지 않습니다.
- S2S API (/verify)는 429를 그대로 반환합니다. (고객사 운영 편의)
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

# Blind 처리할 HTTP 상태 코드 (4xx + 429)
BLIND_STATUS_CODES = {400, 401, 403, 404, 422, 429}

# S2S API 경로 (Blind 예외 - 429를 그대로 반환)
S2S_PATHS = {"/api/v1/captcha/verify"}


async def blind_error_handler(request: Request, exc: HTTPException):
    """
    HTTPException을 BlindError로 변환하는 핸들러
    
    - 4xx 에러: 200 OK + VERIFICATION_FAILED로 변환
    - 429 (Rate Limit): FE는 BlindError, S2S는 429 유지
    - 5xx 에러: 기존 에러 그대로 반환
    """
    # 5xx 에러는 Blind 하지 않음 (서버 오류는 운영자가 알아야 함)
    if exc.status_code >= 500:
        raise exc
    
    # S2S API는 429를 그대로 반환 (고객사 운영 편의)
    if exc.status_code == 429 and request.url.path in S2S_PATHS:
        logger.warning(
            f"[RATE_LIMIT] S2S rate limit - path={request.url.path}",
            extra={"event": "rate_limit", "result": "blocked"}
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Too Many Requests"}
        )
    
    # 4xx 에러 Blind 처리
    if exc.status_code in BLIND_STATUS_CODES:
        # 429(Rate Limit)인 경우 로그에만 원인 기록
        reason = "rate_limited" if exc.status_code == 429 else str(exc.detail)
        
        logger.warning(
            f"[BLIND_ERROR] path={request.url.path} reason={reason}",
            extra={"event": "blind_error", "reason": reason}
        )
        
        # 외부에는 일반 메시지만 (원인 은닉)
        return JSONResponse(
            status_code=200,
            content={
                "status": "FAILED",
                "success": False,
                "error": {
                    "code": "VERIFICATION_FAILED",
                    "message": "다시 시도해주세요."
                },
                "data": None
            }
        )
    
    # 그 외는 기본 처리
    raise exc
