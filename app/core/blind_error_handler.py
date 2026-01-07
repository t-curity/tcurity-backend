# app/core/blind_error_handler.py
"""
BlindError 응답 로직

보안 강화를 위해 4xx 에러를 200 OK + success: false로 변환합니다.
5xx 에러는 Blind 처리하지 않습니다.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

# Blind 처리할 HTTP 상태 코드 (4xx만)
BLIND_STATUS_CODES = {400, 401, 403, 404, 422}


async def blind_error_handler(request: Request, exc: HTTPException):
    """
    HTTPException을 BlindError로 변환하는 핸들러
    
    - 4xx 에러: 200 OK + VERIFICATION_FAILED로 변환
    - 5xx 에러: 기존 에러 그대로 반환
    """
    # 5xx 에러는 Blind 하지 않음 (서버 오류는 운영자가 알아야 함)
    if exc.status_code >= 500:
        raise exc
    
    # 4xx 에러만 Blind 처리
    if exc.status_code in BLIND_STATUS_CODES:
        # 내부 로그 (운영자/디버깅용)
        logger.warning(
            f"[BLIND_ERROR] path={request.url.path} "
            f"method={request.method} "
            f"code={exc.status_code} "
            f"detail={exc.detail}"
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "FAILED",
                "success": False,
                "error": {
                    "code": "VERIFICATION_FAILED",
                    "message": "요청을 처리할 수 없습니다."
                },
                "data": None
            }
        )
    
    # 그 외는 기본 처리
    raise exc
