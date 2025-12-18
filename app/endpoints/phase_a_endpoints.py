# app/endpoints/phase_a_endpoints.py

from fastapi import APIRouter, Header

from app.schemas.common import BaseResponse, ErrorInfo
from app.schemas.error_codes import ErrorCode

from app.core.session_store import get_session_and_validate,update_session, set_session_status
from app.core.state_machine import SessionStatus

from app.services.phase_a_service import generate_phase_a_both
from app.services.logging_service import log_event, LogLevel

router = APIRouter(tags=["CAPTCHA"])


@router.post("/request", response_model=BaseResponse)
def captcha_request_problem(
    session_id: str = Header(..., alias="X-Session-Id")
):
    """
    Phase A 문제 요청 엔드포인트
    - INIT 또는 PHASE_A 상태에서만 호출 가능
    - 서버는 FE용 payload + 내부 정답 데이터(target_path)를 분리하여 저장
    """

    # 세션 확인
    session = get_session_and_validate(session_id)
    # 세션 존재 검증

    current_status = SessionStatus(session["status"])

    # 상태 가드
    if current_status not in (SessionStatus.INIT, SessionStatus.PHASE_A):

        log_event(
            "PHASE_A_INVALID_STATE",
            {
                "session_id": session_id,
                "current_status": current_status.value
            },
            level=LogLevel.WARNING
        )
        return BaseResponse(
            status=current_status.value,
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="현재 단계에서는 Phase A 문제를 요청할 수 없습니다."
            ),
            # 유효한 호출이 아닙니다.
            message="유효한 호출이 아닙니다."
        )

    # Phase A 문제 생성 (FE + Internal)
    fe_payload, internal_payload = generate_phase_a_both()

    # 세션 업데이트 (정답 target_path 저장)
    # 자세한 에러 정보를 남겨도 됨.
    update_session(
        session_id,
        {
            "phase_a": {
                "target_path": internal_payload["target_path"],
                "attempts": session["phase_a"]["attempts"]  # 기존 실패 횟수 유지
            }
        }
    )

    set_session_status(session_id, SessionStatus.PHASE_A)

    # 정상 응답 반환
    return BaseResponse(
        status=SessionStatus.PHASE_A.value,
        success=True,
        data={"problem": fe_payload}
    )
