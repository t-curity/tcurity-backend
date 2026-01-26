# T:CURITY Backend

CAPTCHA 세션 관리 및 검증을 위한 FastAPI 기반 백엔드 서버입니다.

## ✨ 주요 기능

- **세션 관리**: Redis 기반 CAPTCHA 세션 생성/조회/만료
- **Phase A/B 처리**: AI 서버와 연동하여 CAPTCHA 검증 수행
- **S2S 검증**: 서버 간 통신으로 최종 CAPTCHA 결과 검증
- **Rate Limiting**: IP 기반 요청 제한으로 봇 공격 방어
- **클라이언트 인증**: Client ID/Secret 기반 API 인증

## 🛠 기술 스택

- **Framework**: FastAPI
- **Session Store**: Redis
- **Server**: Uvicorn
- **Validation**: Pydantic

## 🚀 시작하기

### 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 환경 변수 (.env)

```ini
INFERENCE_URL=http://10.0.83.48:9000/inference
REDIS_URL=redis://localhost:6379
```

### 실행

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📁 프로젝트 구조

```
tcurity-backend/
├── app/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── endpoints/           # API 라우터
│   │   ├── session_endpoints.py   # 세션 생성/조회
│   │   ├── phase_a_endpoints.py   # Phase A 제출
│   │   ├── verify_endpoints.py    # S2S 검증
│   │   └── health_endpoints.py    # 헬스체크
│   ├── services/            # 비즈니스 로직
│   │   ├── phase_a_service.py     # Phase A 처리
│   │   ├── phase_b_service.py     # Phase B 처리
│   │   ├── verify_service.py      # 검증 로직
│   │   └── ai_phase_*_client.py   # AI 서버 통신
│   ├── schemas/             # Pydantic 모델
│   ├── core/                # 설정, 세션, Rate Limiter
│   └── utils/               # 유틸리티
├── customer-demo/           # 고객사 연동 예제
└── Dockerfile
```

## 🔌 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/session` | 세션 생성 |
| GET | `/api/v1/session/{id}` | 세션 조회 |
| POST | `/api/v1/phase-a/submit` | Phase A 드래그 데이터 제출 |
| POST | `/api/v1/phase-b/submit` | Phase B 이미지 선택 제출 |
| POST | `/api/v1/session/verify` | S2S 최종 검증 |
| GET | `/health` | 서버 상태 |

## ⚙️ 배포

- Main 서버 (10.0.3.151:8000)에서 실행
- Nginx 리버스 프록시를 통해 `/api/*` 라우팅

## 🔀 브랜치 규칙

- `main`: 운영 코드
- `develop`: 개발용
- `feature/*`: 기능 개발

## 📄 라이선스

MIT License - Copyright (c) 2025 T:CURITY