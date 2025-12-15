# schemas/common.py (명세 + 실무 최적화 버전)

from pydantic import BaseModel
from typing import Optional, Any
from app.schemas.error_codes import ErrorCode


class ErrorInfo(BaseModel):
    """
    재시도 응답(Blind Error)에 포함되는 오류 상세 정보
    """
    code: ErrorCode                  # 오류 코드 (WRONG_ANSWER, INVALID_STATE 등)
    message: str                     # 사용자에게 보여줄 메시지
    detail: Optional[Any] = None     # (선택) 내부 디버깅용 정보


class BaseResponse(BaseModel):
    """
    모든 CAPTCHA API의 표준 응답 구조 (HTTP 200 고정)
    """

    # 현재 세션 상태(INIT, PHASE_A, PHASE_B, COMPLETED)
    status: Optional[str] = None     

    # 성공 여부 (성공 시 True, 오류 시 False)
    success: bool = True             

    # 문제/검증 결과 등 실제 페이로드
    data: Optional[Any] = None       

    # 오류 정보 (실패 시 채워짐)
    error: Optional[ErrorInfo] = None

    # Blind Error 사용자 메시지 (ErrorInfo.message와 별도)
    message: Optional[str] = None    