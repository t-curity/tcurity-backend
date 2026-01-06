# 고객사 BE 데모 서버

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
import urllib.error
import json
import os

app = FastAPI(title="Customer Backend Demo")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수 또는 기본값
TCURITY_API_URL = os.getenv("TCURITY_API_URL", "http://localhost:8000")
CLIENT_SECRET_KEY = os.getenv("CLIENT_SECRET_KEY", "demo-secret-key-123")


class VerifyResponse(BaseModel):
    success: bool
    message: str = None
    redirect: bool = False
    redirect_to: str = None


@app.post("/captcha/verify", response_model=VerifyResponse)
def verify_captcha(
    session_id: str = Header(..., alias="X-Session-Id")
):
    """
    고객사 BE → 캡챠 BE S2S 검증 프록시
    
    FE로부터 session_id를 받아 tcurity BE의 /captcha/verify를 호출하고
    결과를 반환합니다.
    """
    url = f"{TCURITY_API_URL}/captcha/verify"
    
    payload = {"session_id": session_id}
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Client-Secret-Key": CLIENT_SECRET_KEY
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            
        print(f"[S2S] tcurity 응답: {result}")
        
        # BLOCKED 상태 처리
        if result.get("status") == "BLOCKED":
            data = result.get("data", {})
            return VerifyResponse(
                success=False,
                message="세션이 차단되었습니다.",
                redirect=data.get("redirect", True),
                redirect_to=data.get("redirect_to", "/")
            )
        
        # 검증 결과 반환
        is_verified = result.get("data", {}).get("verified", False)
        
        return VerifyResponse(
            success=is_verified,
            message="검증 성공" if is_verified else "검증 실패"
        )
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"[ERROR] tcurity API 호출 실패: {e.code} - {error_body}")
        
        raise HTTPException(
            status_code=e.code,
            detail=f"캡챠 서버 오류: {error_body}"
        )
        
    except Exception as e:
        print(f"[ERROR] 알 수 없는 오류: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"내부 서버 오류: {str(e)}"
        )


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
