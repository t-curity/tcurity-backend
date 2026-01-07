# app/endpoints/verify_endpoints.py


from fastapi import APIRouter, Header, HTTPException

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
        print(f"[DEBUG] Phase B 제출 시작 - session_id: {session_id}")
        
        # behavior_pattern_data 필수 검증
        bpd = request.behavior_pattern_data
        
        # if bpd is None:
        #     print(f"[DEBUG] behavior_pattern_data 누락")
        #     return BaseResponse(
        #         status=status.value,
        #         success=False,
        #         error=ErrorInfo(
        #             code=ErrorCode.INVALID_PAYLOAD,
        #             message="behavior_pattern_data는 PHASE_B에서 필수입니다."
        #         )
        #     )

        # if request.user_answer is None:
        #     print(f"[DEBUG] user_answer 누락")
        #     return BaseResponse(
        #         status=status.value,
        #         success=False,
        #         error=ErrorInfo(
        #             code=ErrorCode.INVALID_PAYLOAD,
        #             message="user_answer는 PHASE_B에서 필수입니다."
        #         )
        #     )

        bpd = {"points": request.points, "metadata": request.metadata}
        print(f"[DEBUG] Phase B 검증 호출 - user_answer: {len(request.user_answer)}개")
        return verify_phase_b(session_id, request.user_answer, bpd)


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
from time import time as current_time
from typing import Optional
from app.services.client_validation import validate_client_secret_key
from app.core.session_store import set_session_status
import logging

logger = logging.getLogger(__name__)

class CaptchaVerifyRequest(BaseModel):
    session_id: str

@router.post("/verify", response_model=BaseResponse)
def captcha_verify(
    req: CaptchaVerifyRequest,
    client_secret_key: Optional[str] = Header(None, alias="X-Client-Secret-Key")
):
    """
    S2S 최종 검증 API (Replay-Block 적용)
    - 고객사 BE에서 세션 검증 시 사용
    - X-Client-Secret-Key 헤더 필수
    - COMPLETED 상태만 1회 검증 가능 → VERIFIED로 전이
    - VERIFIED/BLOCKED 상태는 Replay 차단
    """
    # 1. 클라이언트 인증
    client = validate_client_secret_key(client_secret_key)
    logger.info(f"[S2S] 인증 성공 - client_id: {client.get('client_id')}")
    
    # 2. 세션 검증
    session = get_session_and_validate(req.session_id)
    current = SessionStatus(session["status"])
    
    # 3. Replay-Block: VERIFIED 상태 (이미 검증됨)
    if current == SessionStatus.VERIFIED:
        logger.warning(f"[REPLAY] 이미 검증된 세션 재요청 - session_id: {req.session_id}")
        raise HTTPException(status_code=403, detail="ALREADY_VERIFIED")
    
    # 4. Replay-Block: BLOCKED 상태 (차단된 세션)
    if current == SessionStatus.BLOCKED:
        logger.warning(f"[REPLAY] 차단된 세션 재요청 - session_id: {req.session_id}")
        raise HTTPException(status_code=403, detail="SESSION_BLOCKED")
    
    # 5. COMPLETED 상태: 1회 검증 성공 → VERIFIED로 전이
    if current == SessionStatus.COMPLETED:
        # 상태 전이 (원자적)
        set_session_status(req.session_id, SessionStatus.VERIFIED)
        
        logger.info(f"[S2S] 검증 성공 - session_id: {req.session_id}")
        
        return BaseResponse(
            status=SessionStatus.VERIFIED.value,
            success=True,
            data={
                "session_id": req.session_id,
                "verified": True,
                "verified_at": int(current_time() * 1000),
                "phase_b_attempts": session.get("phase_b", {}).get("fail_count", 0)
            }
        )
    
    # 6. 그 외 상태 (INIT, PHASE_A, PHASE_B 등)
    logger.warning(f"[S2S] 잘못된 상태에서 검증 요청 - session_id: {req.session_id}, status: {current.value}")
    raise HTTPException(status_code=400, detail="INVALID_STATE")