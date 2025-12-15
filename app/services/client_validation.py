# app/services/client_validation.py

from fastapi import HTTPException, status
from typing import Dict

# (가정) 실제 운영 시, 이 맵은 DB나 설정 파일에서 로드됩니다.
VALID_CLIENTS: Dict[str, str] = {
    "cust_alpha": "Active",
    "cust_beta": "Active",
    # ...
}

def validate_client_id(client_id: str):
    """
    X-Client-Id의 유효성을 검증하고, 유효하지 않으면 401 UNVERIFIED 오류를 발생시킵니다.
    """
    if client_id not in VALID_CLIENTS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "UNVERIFIED",
                "message": "허용되지 않은 client_id 입니다."
            }
        )
    
    # 추가적인 상태 체크 로직 (e.g., 계정 상태가 'Active'인지)
    # if VALID_CLIENTS[client_id] != "Active":
    #     ...
    
    return True # 유효하면 통과