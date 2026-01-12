# app/endpoints/health_endpoints.py
"""
헬스체크 엔드포인트

- /health: 기본 헬스체크 (서버 생존 확인)
- /health/ready: 의존성 체크 (Redis, AI 서버) - 정보 노출 최소화
"""

from fastapi import APIRouter
from functools import lru_cache
import time
import logging
import httpx

from app.core.config import AI_SERVER_URL

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)

# 캐시 TTL (초)
_readiness_cache = {"result": True, "checked_at": 0}
READINESS_CACHE_TTL = 2  # 2초 캐시


# =====================================================
# 의존성 체크 함수
# =====================================================

def check_ai_server(timeout: float = 2.0) -> bool:
    """AI 서버 연결 체크 (빠른 타임아웃)"""
    try:
        # 간단한 GET 요청으로 연결 확인
        response = httpx.get(f"{AI_SERVER_URL}/health", timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"AI server health check failed: {e}")
        return False


def get_readiness_with_cache() -> bool:
    """Readiness 체크 (캐싱 적용)"""
    global _readiness_cache
    
    now = time.time()
    if now - _readiness_cache["checked_at"] < READINESS_CACHE_TTL:
        return _readiness_cache["result"]
    
    # 의존성 체크
    ai_ok = check_ai_server(timeout=2.0)
    # Redis는 현재 In-Memory 사용 중이므로 항상 True
    redis_ok = True
    
    is_ready = ai_ok and redis_ok
    
    # 캐시 업데이트
    _readiness_cache["result"] = is_ready
    _readiness_cache["checked_at"] = now
    
    # 실패 시 로그에만 기록 (외부 노출 안함)
    if not is_ready:
        logger.error(
            "Readiness check failed",
            extra={"ai_server": ai_ok, "redis": redis_ok}
        )
    
    return is_ready


# =====================================================
# 엔드포인트
# =====================================================

@router.get("/health")
def health():
    """
    기본 헬스체크 - 서버 생존 확인
    항상 단순 응답 반환
    """
    return {"status": "ok"}


@router.get("/health/ready")
def readiness():
    """
    Readiness 체크 - 의존성 상태 확인
    
    보안: 세부 원인은 로그에만 기록, 외부에는 ok/fail만 반환
    성능: 2초 캐싱으로 빈번한 체크 방지
    """
    is_ready = get_readiness_with_cache()
    
    # 외부에는 단순 응답만 (세부 원인 노출 안함)
    return {"status": "ok" if is_ready else "fail"}
