# app/services/session_service.py

from typing import Dict, Any

# core에서 세션 생성 로직과 TTL 설정을 가져옵니다.
from app.core.session_store import create_session as core_create_session 
# from app.core import config # config가 있다면 여기서 가져옵니다.

def initialize_session(client_id: str) -> Dict[str, Any]:
    """
    클라이언트 ID를 기반으로 세션을 생성하고, API 응답에 필요한 
    데이터(status, session_id, expires_in)를 dict 형태로 반환합니다.
    
    Args:
        client_id: 유효성이 검증된 고객 ID (X-Client-Id)
    """
    
    # 코어 레이어의 세션 생성 로직을 호출하여 세션을 저장하고 응답 데이터를 받습니다.
    # core_create_session 함수가 이미 SESSION_STORE에 저장까지 완료합니다.
    session_response_data = core_create_session(client_id=client_id)
    
    # session_response_data는 이미 { "status": "INIT", "session_id": "...", "expires_in": 600 } 형태입니다.
    return session_response_data