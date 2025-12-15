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

BOT_SCORE_THRESHOLD = 0.5         # Phase A threshold
BOT_BEHAVIOR_THRESHOLD = 0.85     # Phase B threshold
PHASE_B_TIME_LIMIT = 30           # seconds


# -------------------- Feature Extraction --------------------
def extract_features(target_path, user_path):
    return [0.12, 0.52, 0.05, 1350.0]  # Dummy


def predict_anomaly(feature_vector):
    return 0.3  # Dummy score


# ============================================================
#   PHASE A 검증
# ============================================================
def verify_phase_a(session_id: str, behavior_pattern_data) -> BaseResponse:

    session = get_session_and_validate(session_id)
    current = SessionStatus(session["status"])

    if current != SessionStatus.PHASE_A:
        return BaseResponse(
            status=current.value,
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="PHASE_A 상태에서만 검증 가능합니다."
            )
        )

    target = session["phase_a"]["target_path"]
    attempts = session["phase_a"]["attempts"]
    
    feature = extract_features(target, behavior_pattern_data)

    # 테스트용: 첫 시도 실패, 두 번째 성공
    if attempts == 0:
        anomaly_score = 0.8   # 실패
    else:
        anomaly_score = 0.2   # 성공

    attempts = session["phase_a"]["attempts"]

    # ---------------- SUCCESS -> Phase B 전환 ----------------
    if anomaly_score < BOT_SCORE_THRESHOLD:

        set_session_status(session_id, SessionStatus.PHASE_B)
        fail_count = session["phase_b"]["fail_count"]

        fe_payload, internal_payload = generate_phase_b_both(fail_count)

        update_session(session_id, {
            "phase_b": {
                "correct_answer": internal_payload["correct_answer"],
                "issued_at": internal_payload["issued_at"],
                "fail_count": fail_count
            }
        })

        return BaseResponse(
            status=SessionStatus.PHASE_B.value,
            success=True,
            data={"problem": fe_payload}
        )

    # ---------------- FAIL: 다시 A 문제 생성 ----------------
    fe_payload, internal_payload = generate_phase_a_both()

    update_session(session_id, {
        "phase_a": {
            "attempts": session["phase_a"]["attempts"] + 1,
            "target_path": internal_payload["target_path"]
        }
    })

    return BaseResponse(
        status=SessionStatus.PHASE_A.value,
        success=False,
        data={"problem": fe_payload},
        error=ErrorInfo(
            code=ErrorCode.LOW_CONFIDENCE_BEHAVIOR,
            message="행동 패턴이 비정상적으로 감지되었습니다."
        )
    )


# ============================================================
#   PHASE B 검증
# ============================================================
def check_phase_b_behavior(behavior):
    if not behavior:
        return True
    return 0.95 >= BOT_BEHAVIOR_THRESHOLD  # Dummy


def handle_phase_b_fail(session_id: str, session: Dict[str, Any], fail_count: int, error):
    """
    실패 시 fail_count 증가 및 새로운 문제 발급
    """
    new_fail = fail_count + 1

    fe_payload, internal_payload = generate_phase_b_both(new_fail)

    update_session(session_id, {
        "phase_b": {
            "correct_answer": internal_payload["correct_answer"],
            "issued_at": internal_payload["issued_at"],
            "fail_count": new_fail
        }
    })

    return BaseResponse(
        status=SessionStatus.PHASE_B.value,
        success=False,
        data={"problem": fe_payload},
        error=ErrorInfo(
            code=error,
            message="정답이 올바르지 않거나 행동 분석 실패"
        )
    )


def verify_phase_b(session_id: str, user_answer: List[str], behavior) -> BaseResponse:

    session = get_session_and_validate(session_id)
    current = SessionStatus(session["status"])

    if current != SessionStatus.PHASE_B:
        return BaseResponse(
            status=current.value,
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="PHASE_B 상태에서만 검증 가능합니다."
            )
        )

    issued_at = session["phase_b"]["issued_at"]
    correct = session["phase_b"]["correct_answer"]
    fail_count = session["phase_b"]["fail_count"]

    elapsed = (int(time() * 1000) - issued_at) / 1000

    # 시간 초과
    if elapsed > PHASE_B_TIME_LIMIT:
        return handle_phase_b_fail(session_id, session, fail_count, ErrorCode.TIME_LIMIT_EXCEEDED)

    is_correct = user_answer == correct
    is_human = check_phase_b_behavior(behavior)

    if is_correct and is_human:
        set_session_status(session_id, SessionStatus.COMPLETED)
        return BaseResponse(
            status=SessionStatus.COMPLETED.value,
            success=True,
            data={"message": "CAPTCHA 인증 완료"}
        )

    error = ErrorCode.WRONG_ANSWER if not is_correct else ErrorCode.ANOMALOUS_BEHAVIOR
    return handle_phase_b_fail(session_id, session, fail_count, error)
