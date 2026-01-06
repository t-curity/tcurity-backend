# 고객사 BE 데모 서버

## 개요

고객사 백엔드 데모 서버입니다. 프론트엔드로부터 `X-Session-Id` 헤더를 받아 tcurity BE의 `/captcha/verify` API를 S2S로 호출합니다.

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (포트 9001)
uvicorn main:app --port 9001 --reload
```

## API

### POST /captcha/verify

**Request Headers:**
```
X-Session-Id: {session_id}
```

**Response:**
```json
{
  "success": true,
  "message": "검증 성공"
}
```

**BLOCKED 시:**
```json
{
  "success": false,
  "message": "세션이 차단되었습니다.",
  "redirect": true,
  "redirect_to": "/"
}
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| TCURITY_API_URL | http://localhost:8000 | tcurity BE URL |
| CLIENT_SECRET_KEY | demo-secret-key-123 | 클라이언트 시크릿 키 |
