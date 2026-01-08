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
from app.services.ai_phase_b_client import verify_phase_b_with_ai


PHASE_B_TIME_LIMIT = 30  # seconds
PHASE_B_MAX_FAIL_COUNT = 3  # 최대 실패 횟수


def calculate_difficulty_from_confidence(confidence: float) -> str:
    """
    Phase A AI confidence 기반 Phase B 난이도 계산
    
    Args:
        confidence: AI 서버가 반환한 사람 확률 (0.0 ~ 1.0)
        
    Returns:
        'NORMAL', 'MEDIUM', 'HIGH'
    
    로직:
        - confidence >= 0.8: 확실히 사람 → NORMAL (노이즈 없음)
        - 0.5 <= confidence < 0.8: 애매함 → MEDIUM (약한 노이즈)
        - confidence < 0.5: 봇에 가까움 → HIGH (강한 노이즈)
    """
    if confidence >= 0.7:
        return "NORMAL"
    elif confidence >= 0.55:
        return "MEDIUM"
    else:
        return "HIGH"


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
    confidence = 1.0  # 기본값 (AI 서버 응답 없으면 사람으로 간주)
    try:
        # FE payload에서 points와 metadata 추출
        points = behavior_pattern_data.get("points", [])
        metadata = behavior_pattern_data.get("metadata", {})
        
        ai_result = verify_phase_a_with_ai(points, metadata)
        is_human = ai_result.get("pass", False)
        # AI 서버가 confidence를 반환하면 사용, 없으면 기본값 유지
        confidence = ai_result.get("confidence", 1.0 if is_human else 0.0)
    except Exception:
        # AI 서버 오류는 보안상 FAIL 처리
        is_human = False
        confidence = 0.0

    # ==================================================
    #   SUCCESS (is_human=True) → Phase B 진입
    #   - 사람이지만 confidence가 낮으면 어려운 난이도
    # ==================================================
    if is_human:
        set_session_status(session_id, SessionStatus.PHASE_B)

        fail_count = session["phase_b"]["fail_count"]
        
        # confidence 기반 난이도 계산
        # - 높은 confidence → NORMAL
        # - 낮은 confidence (봇에 가까움) → MEDIUM/HIGH
        difficulty = calculate_difficulty_from_confidence(confidence)
        print(f"[DEBUG] Phase B 진입 - confidence: {confidence}, difficulty: {difficulty}")

        fe_payload, internal_payload = generate_phase_b_both(fail_count, difficulty)

        update_session(
            session_id,
            {
                "phase_b": {
                    "correct_uuids": internal_payload["correct_uuids"],
                    "issued_at": internal_payload["issued_at"],
                    "fail_count": fail_count,
                    "difficulty": difficulty,
                    "confidence": confidence,
                }
            },
        )

        return BaseResponse(
            status=SessionStatus.PHASE_B.value,
            success=True,
            data={"problem": fe_payload},
        )

    # ==================================================
    #   FAIL (is_human=False, 봇 판정) → Phase A 재시도
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
        success=True,
        status=SessionStatus.PHASE_A.value,
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
    - 최대 실패 횟수(3회) 초과 시 세션 차단
    """
    new_fail = fail_count + 1
    
    # 최대 실패 횟수 초과 시 세션 차단
    if new_fail > PHASE_B_MAX_FAIL_COUNT:
        set_session_status(session_id, SessionStatus.BLOCKED)
        return BaseResponse(
            status=SessionStatus.BLOCKED.value,
            success=False,
            error=ErrorInfo(
                code=ErrorCode.MAX_ATTEMPTS_EXCEEDED,
                message=f"최대 실패 횟수({PHASE_B_MAX_FAIL_COUNT}회)를 초과했습니다.",
            ),
            data={
                "redirect": True,
                "redirect_to": "/",  # 첫 페이지로 리다이렉트
                "message": "세션이 차단되었습니다. 처음부터 다시 시작해주세요."
            }
        )
    
    # 세션에서 저장된 난이도 가져오기 (없으면 NORMAL)
    difficulty = session["phase_b"].get("difficulty", "NORMAL")

    fe_payload, internal_payload = generate_phase_b_both(new_fail, difficulty)

    update_session(
        session_id,
        {
            "phase_b": {
                "correct_uuids": internal_payload["correct_uuids"],
                "issued_at": internal_payload["issued_at"],
                "fail_count": new_fail,
                "difficulty": difficulty,
            }
        },
    )

    return BaseResponse(
        status=SessionStatus.PHASE_B.value,  # 여전히 PHASE_B 상태
        success=True,
        data={"problem": fe_payload},
        error=ErrorInfo(
            code=error,
            message="정답이 올바르지 않거나 행동 분석 실패",
        ),
    )



def verify_phase_b(
    session_id: str,
    user_answer: List[str],
    behavior_pattern_data: Dict[str, Any],
) -> BaseResponse:
    """
    Phase B 정답 + 행동 검증
    
    Args:
        session_id: 세션 ID
        user_answer: 사용자가 선택한 이미지 UUID 리스트
        behavior_pattern_data: 행동 패턴 데이터 {"points": [...], "metadata": {...}}
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
    # correct_numbers = session["phase_b"]["correct_numbers"]  # 순서 검증용 (주석)
    # number_to_index = session["phase_b"]["number_to_index"]  # 순서 검증용 (주석)
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

    # ---------------- 정답 + 순서 검증 (백엔드) ----------------
    # 사용자가 선택한 UUID와 정답 UUID를 순서까지 비교
    # 순서가 틀리면 AI 서버로 넘어가지 않고 즉시 실패 처리
    correct_uuids = session["phase_b"]["correct_uuids"]
    
    # 리스트 직접 비교 (순서 + 값 모두 일치해야 통과)
    is_correct = user_answer == correct_uuids
    
    # ========== 테스트용 콘솔 출력 ==========
    print(f"\n{'='*50}")
    print(f"[PHASE B 검증 결과]")
    print(f"  - 사용자 답변: {user_answer}")
    print(f"  - 정답: {correct_uuids}")
    print(f"  - 결과: {'✅ 정답!' if is_correct else '❌ 오답'}")
    print(f"{'='*50}\n")
    
    if not is_correct:
        return handle_phase_b_fail(
            session_id,
            session,
            fail_count,
            ErrorCode.WRONG_ANSWER,
        )

    # ---------------- AI 서버 호출 (Phase B) ----------------
    # 정답이 맞으면 AI 서버에서 행동 패턴만 검증
    try:
        # FE payload에서 points와 metadata 추출
        points = behavior_pattern_data.get("points", [])
        metadata = behavior_pattern_data.get("metadata", {})
        
        # AI 서버에 행동 데이터만 전송 (정답은 백엔드에서 이미 검증)
        ai_result = verify_phase_b_with_ai(points, metadata)
        is_human = ai_result.get("pass", False)
    except Exception:
        # AI 서버 오류 시 정답만 맞으면 통과 (AI 모델 준비 전)
        is_human = True


    # 행동 검증 결과 처리
    if is_human:
        set_session_status(session_id, SessionStatus.COMPLETED)
        return BaseResponse(
            status=SessionStatus.COMPLETED.value,  # COMPLETED 상태
            success=True,
        )


    # AI 서버가 봇으로 판단
    return handle_phase_b_fail(
        session_id,
        session,
        fail_count,
        ErrorCode.ANOMALOUS_BEHAVIOR,
    )

