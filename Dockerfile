FROM python:3.11-slim

WORKDIR /app

# (선택) 빌드에 필요한 패키지 있는 경우 대비
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# FastAPI 기본 포트
EXPOSE 8000

# 환경에 맞게 app.main:app 부분만 맞춰줘
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
