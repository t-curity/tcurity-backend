# T-CURITY Backend (FastAPI)
CAPTCHA 검증을 위한 FastAPI 기반 백엔드 서버입니다.

## 📌 프로젝트 구조
```
app/
├── main.py # 엔트리 포인트
├── routers/ # API 라우터
├── services/ # 비즈니스 로직
├── models/ # 데이터 모델
└── core/ # 환경설정

```
---

## 📌 실행 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
---

## 📌 환경변수 예시 (.env)

```ini
INFERENCE_URL=http://10.0.83.48:9000/inference
REDIS_URL=redis://localhost:6379
```

---

## 📌 브랜치 규칙
main: 운영 코드
develop: 개발용
feature/*: 기능 개발 브랜치