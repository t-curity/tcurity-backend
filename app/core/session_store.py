# core/session_store.py

from uuid import uuid4
from time import time
from typing import Dict, Any

from fastapi import HTTPException, status
from app.core.state_machine import SessionStatus, STATE_TRANSITION_RULES # 1210 enum 도입 + 헬퍼 추가


# In-Memory Store
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

# 설정 (TODO: config.py로 분리 가능)
SESSION_TTL_SECONDS = 600   # 10분


# -----------------------
# Session 생성
# -----------------------
def create_session(client_id: str) -> Dict[str, Any]:
    """
    새로운 CAPTCHA 세션을 생성하고 SESSION_STORE에 저장
    """
    session_id = str(uuid4())
    now_ms = int(time() * 1000)

    session_data = {
        "session_id": session_id,
        "client_id": client_id,
        "status": SessionStatus.INIT.value,  # Enum으로 향후 대체 추천 / 1210 enum 기반으로 통일

        "created_at": now_ms,
        "expires_at": now_ms + (SESSION_TTL_SECONDS * 1000),

        "phase_a": {
            "target_path": [],
            "attempts": 0
        },

        "phase_b": {
            "correct_answer": [],
            "fail_count": 0,
            "issued_at": 0
        }
    }

    SESSION_STORE[session_id] = session_data

    # API 응답 구조
    return {
        "status": session_data["status"],
        "session_id": session_id,
        "expires_in": SESSION_TTL_SECONDS
    }


# -----------------------
# 세션 조회 + 유효성 검사
# -----------------------
def get_session_and_validate(session_id: str) -> Dict[str, Any]:
    """
    FastAPI 환경에 최적화된 세션 조회 함수
    세션이 없거나 만료된 경우 HTTPException 발생
    """
    session = SESSION_STORE.get(session_id)

    if session is None:
        raise HTTPException(404, "SESSION_NOT_FOUND")

    if is_session_expired(session):
        raise HTTPException(403, "SESSION_EXPIRED")
        
    return session

# -----------------------
# 상태 전이 + 로그 (중요)
# -----------------------
def set_session_status(session_id: str, new_status: SessionStatus):
    """
    상태 전이를 안전하게 수행하고 로그 출력.
    모든 서비스는 문자열로 상태 업데이트하지 말고 이 함수를 사용해야 함.
    """
    if session_id not in SESSION_STORE:
        raise HTTPException(404, "SESSION_NOT_FOUND")

    session = SESSION_STORE[session_id]

    old_status = SessionStatus(session["status"])
#    new_status = SessionStatus(new_status)  # 혹시 문자열 들어올 때 대비

    if not isinstance(new_status, SessionStatus):
        new_status = SessionStatus(new_status)
        
    # 1) 전이 가능한 상태인지 확인 (state_machine RULES)
    allowed = STATE_TRANSITION_RULES.get(old_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"INVALID_STATE_TRANSITION: {old_status.value} → {new_status.value}"
        )

    # 2) 상태 실제 업데이트
    session["status"] = new_status.value

    # 3) 디버그 로그 출력
    print(f"[STATE] {old_status.value} → {new_status.value}  (session_id={session_id})")


# -----------------------
# 세션 업데이트 (안전한 딕셔너리 병합)
# -----------------------
def update_session(session_id: str, data: Dict[str, Any]):
    if session_id not in SESSION_STORE:
        raise HTTPException(404, "SESSION_NOT_FOUND")

    session = SESSION_STORE[session_id]

    # 깊은 병합 (중첩 dict만 update)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(session.get(key), dict):
            session[key].update(value)
        else:
            session[key] = value



# # -----------------------
# # 상태 전용 업데이트 헬퍼 (1210)
# # -----------------------
# def set_session_status(session_id: str, new_status: SessionStatus):
#     """
#     SessionStatus Enum을 사용해 status 필드를 안전하게 변경하는 헬퍼.
#     서비스 레이어에서는 문자열 대신 이 함수를 사용하도록 통일.
#     """
#     update_session(session_id, {"status": new_status.value})


# -----------------------
# TTL 체크
# -----------------------
def is_session_expired(session: Dict[str, Any]) -> bool:
    return int(time() * 1000) > session["expires_at"]