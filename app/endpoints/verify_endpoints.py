# app/endpoints/verify_endpoints.py


from fastapi import APIRouter, Header

from app.schemas.captcha_submit import CaptchaSubmitRequest
from app.schemas.common import BaseResponse, ErrorInfo
from app.schemas.error_codes import ErrorCode

from app.core.session_store import get_session_and_validate
from app.core.state_machine import SessionStatus

from app.services.verify_service import verify_phase_a, verify_phase_b

router = APIRouter(tags=["CAPTCHA Submit"])


@router.post("/submit", response_model=BaseResponse)
def captcha_submit(
    request: CaptchaSubmitRequest,
    session_id: str = Header(..., alias="X-Session-Id")
):

    session = get_session_and_validate(session_id)
    status = SessionStatus(session["status"])

    # -------------------------
    # PHASE A 처리
    # -------------------------
    if status == SessionStatus.PHASE_A:
        bpd = request.behavior_pattern_data
        if bpd is None and request.points is not None and request.metadata is not None:
            bpd = {"points": request.points, "metadata": request.metadata}

        if bpd is None:
            return BaseResponse(
                status=status.value,
                success=False,
                error=ErrorInfo(code=ErrorCode.INVALID_PAYLOAD,
                                message="behavior_pattern_data는 PHASE_A에서 필수입니다.")
            )

        return verify_phase_a(session_id, bpd)

    # -------------------------
    # PHASE B 처리
    # -------------------------
    if status == SessionStatus.PHASE_B:

        if request.user_answer is None:
            return BaseResponse(
                status=status.value,
                success=False,
                error=ErrorInfo(
                    code=ErrorCode.INVALID_PAYLOAD,
                    message="user_answer는 PHASE_B에서 필수입니다."
                )
            )

        return verify_phase_b(session_id, request.user_answer, request.behavior_pattern_data)

    # -------------------------
    # COMPLETED 처리
    # -------------------------
    if status == SessionStatus.COMPLETED:
        
        return BaseResponse(
            status=status.value,
            success=False,
            error=ErrorInfo(
                code=ErrorCode.INVALID_STATE,
                message="이미 완료된 세션입니다."
            )
        )

    # -------------------------
    # 그 외 상태
    # -------------------------
    return BaseResponse(
        status=status.value,
        success=False,
        error=ErrorInfo(
            code=ErrorCode.INVALID_STATE,
            message=f"현재 상태({status.value})에서는 제출할 수 없습니다."
        )
    )

from pydantic import BaseModel

class CaptchaVerifyRequest(BaseModel):
    session_id: str

@router.post("/verify", response_model=BaseResponse)
def captcha_verify(req: CaptchaVerifyRequest):
    session = get_session_and_validate(req.session_id)
    status = SessionStatus(session["status"])
    return BaseResponse(
        status=status.value,
        success=(status == SessionStatus.COMPLETED),
        data={"session_id": req.session_id}
    )