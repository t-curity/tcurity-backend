# app/core/rate_limiter.py
"""
Rate Limiting 설정

- 엔드포인트별 키 함수 분리
- session_id, client_secret, IP 기반 제한
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


# =====================================================
# 키 추출 함수 (엔드포인트별로 다르게 사용)
# =====================================================

def key_by_session(request: Request) -> str:
    """
    /captcha/submit용 키 함수
    session_id 앞 6자 + IP 조합
    """
    session_id = request.headers.get("X-Session-Id", "")[:6]
    ip = get_remote_address(request)
    return f"session:{session_id}:{ip}"


def key_by_client_secret(request: Request) -> str:
    """
    /captcha/verify (S2S)용 키 함수
    client_secret 기반 (IP보다 안정적)
    """
    client_secret = request.headers.get("X-Client-Secret-Key", "")
    if client_secret:
        # 키의 앞부분만 사용 (보안)
        return f"client:{client_secret[:8]}"
    return f"ip:{get_remote_address(request)}"


def key_by_ip(request: Request) -> str:
    """
    기본 IP 기반 키 함수
    """
    return f"ip:{get_remote_address(request)}"


# =====================================================
# Limiter 인스턴스
# =====================================================

# 기본 limiter (IP 기반)
limiter = Limiter(key_func=key_by_ip)


# =====================================================
# Rate Limit 설정값
# =====================================================

RATE_LIMITS = {
    "submit": "10/minute",      # /captcha/submit
    "request": "20/minute",     # /captcha/request
    "verify": "60/minute",      # /captcha/verify (S2S)
}
