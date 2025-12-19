# app/services/verify_service.py

from time import time
from typing import List, Dict, Any

from app.schemas.common import BaseResponse, ErrorInfo
from app.schemas.error_codes import ErrorCode

from app.core.state_machine import SessionStatus
from app.core.session_store import (
    get_session_and_validate,
    update_session,
    set_session_status,
)

from app.services.phase_a_service import generate_phase_a_both
from app.services.phase_b_service import generate_phase_b_both
from app.services.ai_phase_a_client import verify_phase_a_with_ai


PHASE_B_TIME_LIMIT = 30  # seconds


# ============================================================
#   PHASE A 검증 (AI 연동)
# ============================================================
def verify_phase_a(
    session_id: str,
    behavior_pattern_data: Dict[str, Any],
) -> BaseResponse:
    """
    Phase A 사용자 행동을 AI 서버에 위임하여 검증한다.
    """

    session = get_session_and_validate(session_id)
    current = SessionStatus(session["status"])

    # ---------------- 상태 검증 ----------------
    if current != SessionStatus.PHASE_A:
        return BaseResponse(
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="PHASE_A 상태에서만 검증 가능합니다.",
            ),
        )

    # ---------------- AI 서버 호출 ----------------
    try:
        # FE payload에서 points와 metadata 추출
        points = behavior_pattern_data.get("points", [])
        metadata = behavior_pattern_data.get("metadata", {})
        
        ai_result = verify_phase_a_with_ai(points, metadata)
        is_human = ai_result.get("pass", False)
    except Exception:
        # AI 서버 오류는 보안상 FAIL 처리
        is_human = False

    # ==================================================
    #   SUCCESS → Phase B 진입
    # ==================================================
    if is_human:
        set_session_status(session_id, SessionStatus.PHASE_B)

        fail_count = session["phase_b"]["fail_count"]

        fe_payload, internal_payload = generate_phase_b_both(fail_count)

        update_session(
            session_id,
            {
                "phase_b": {
                    "correct_answer": internal_payload["correct_answer"],
                    "issued_at": internal_payload["issued_at"],
                    "fail_count": fail_count,
                }
            },
        )

        return BaseResponse(
            success=True,
            data={"problem": fe_payload},
        )

    # ==================================================
    #   FAIL → Phase A 재시도
    # ==================================================
    fe_payload, internal_payload = generate_phase_a_both()

    update_session(
        session_id,
        {
            "phase_a": {
                "attempts": session["phase_a"]["attempts"] + 1,
                "target_path": internal_payload["target_path"],
            }
        },
    )

    return BaseResponse(
        success=False,
        data={"problem": fe_payload},
        error=ErrorInfo(
            code=ErrorCode.LOW_CONFIDENCE_BEHAVIOR,
            message="행동 패턴이 비정상적으로 감지되었습니다.",
        ),
    )


# ============================================================
#   PHASE B 검증
# ============================================================
def check_phase_b_behavior(behavior) -> bool:
    """
    Phase B 행동 검증 (현재는 더미)
    """
    if not behavior:
        return True
    return True  # 추후 AI 연동 예정


def handle_phase_b_fail(
    session_id: str,
    session: Dict[str, Any],
    fail_count: int,
    error: ErrorCode,
) -> BaseResponse:
    """
    Phase B 실패 처리:
    - fail_count 증가
    - 새로운 문제 발급
    """
    new_fail = fail_count + 1

    fe_payload, internal_payload = generate_phase_b_both(new_fail)

    update_session(
        session_id,
        {
            "phase_b": {
                "correct_answer": internal_payload["correct_answer"],
                "issued_at": internal_payload["issued_at"],
                "fail_count": new_fail,
            }
        },
    )

    return BaseResponse(
        success=False,
        data={"problem": fe_payload},
        error=ErrorInfo(
            code=error,
            message="정답이 올바르지 않거나 행동 분석 실패",
        ),
    )


def verify_phase_b(
    session_id: str,
    user_answer: List[str],
    behavior,
) -> BaseResponse:
    """
    Phase B 정답 + 행동 검증
    """

    session = get_session_and_validate(session_id)
    current = SessionStatus(session["status"])

    if current != SessionStatus.PHASE_B:
        return BaseResponse(
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="PHASE_B 상태에서만 검증 가능합니다.",
            ),
        )

    issued_at = session["phase_b"]["issued_at"]
    correct = session["phase_b"]["correct_answer"]
    fail_count = session["phase_b"]["fail_count"]

    elapsed = (int(time() * 1000) - issued_at) / 1000

    # ---------------- 시간 초과 ----------------
    if elapsed > PHASE_B_TIME_LIMIT:
        return handle_phase_b_fail(
            session_id,
            session,
            fail_count,
            ErrorCode.TIME_LIMIT_EXCEEDED,
        )

    is_correct = user_answer == correct
    is_human = check_phase_b_behavior(behavior)

    if is_correct and is_human:
        set_session_status(session_id, SessionStatus.COMPLETED)
        return BaseResponse(
            success=True,
            data={"message": "CAPTCHA 인증 완료"},
        )

    error = (
        ErrorCode.WRONG_ANSWER
        if not is_correct
        else ErrorCode.ANOMALOUS_BEHAVIOR
    )

    return handle_phase_b_fail(
        session_id,
        session,
        fail_count,
        error,
    )
