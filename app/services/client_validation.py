# app/services/client_validation.py

import json
import os
from fastapi import HTTPException, status
from typing import Dict, Any, Optional

# JSON 파일 경로
CREDENTIALS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "client_credentials.json"
)

# 클라이언트 정보 캐시 (서버 시작 시 로드)
_client_cache: Dict[str, Dict[str, Any]] = {}


def load_client_credentials():
    """
    서버 시작 시 client_credentials.json에서 클라이언트 정보 로드
    """
    global _client_cache
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"[WARNING] client_credentials.json 파일 없음: {CREDENTIALS_FILE}")
        return
    
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # secret_key를 키로 하는 딕셔너리로 변환
        for client in data.get("clients", []):
            secret_key = client.get("secret_key")
            if secret_key:
                _client_cache[secret_key] = client
                
        print(f"[INFO] 클라이언트 인증 정보 로드 완료: {len(_client_cache)}개")
        
    except Exception as e:
        print(f"[ERROR] 클라이언트 정보 로드 실패: {e}")


# 서버 시작 시 자동 로드
load_client_credentials()


def validate_client_secret_key(secret_key: Optional[str]) -> Dict[str, Any]:
    """
    X-Client-Secret-Key 헤더의 유효성을 검증합니다.
    
    Args:
        secret_key: 클라이언트가 보낸 시크릿 키
        
    Returns:
        클라이언트 정보 딕셔너리
        
    Raises:
        HTTPException: 인증 실패 시
    """
    if not secret_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "MISSING_SECRET_KEY",
                "message": "X-Client-Secret-Key 헤더가 필요합니다."
            }
        )
    
    client = _client_cache.get(secret_key)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_SECRET_KEY",
                "message": "유효하지 않은 시크릿 키입니다."
            }
        )
    
    return client


def validate_client_id(client_id: str):
    """
    X-Client-Id의 유효성을 검증합니다. (기존 호환용)
    """
    # 기존 로직 유지 (필요 시)
    return True