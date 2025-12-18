# app/endpoints/session_endpoints.py

from fastapi import APIRouter, Header, HTTPException, status

from app.schemas.session import BaseResponse
from app.services.session_service import initialize_session
from app.services.client_validation import validate_client_id  # optional: validator 분리


router = APIRouter(tags=["Session"]) 


@router.post("/init", response_model=BaseResponse)
def session_init_endpoint(
    x_client_id: str = Header(..., alias="X-Client-Id")
):
    """
    1.1 세션 초기화 (Init)
    - 클라이언트 인증
    - 새로운 CAPTCHA 세션 발급
    """

    # 1) client_id 검증 (별도 서비스로 분리하는 것이 더 정석적)
    # validate_client_id(x_client_id)

    # 2) 세션 생성 서비스 호출
    session_data = initialize_session(client_id=x_client_id)
    
    # 3) 통일된 응답 구조로 반환 (data 안에 모든 정보)
    return BaseResponse(
        success=True,
        data={
            "session_id": session_data["session_id"],
            #"expires_in": session_data["expires_in"]
        }
    )
