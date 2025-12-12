from fastapi import FastAPI
from app.routers import captcha

app = FastAPI(
    title="T-CURITY Backend API",
    description="CAPTCHA verification API server",
    version="1.0.0"
)

# Router 등록
app.include_router(captcha.router)

@app.get("/health")
def health():
    return {"status": "ok"}
